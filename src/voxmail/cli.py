"""Phase 1 interface: talk to the agent in the terminal. Contacts and sending are fake."""

import select
import sys
import time
from datetime import timedelta

from voxmail.agent.agent import Agent
from voxmail.config import get_settings
from voxmail.contacts.directory import JsonContactDirectory
from voxmail.domain.models import Action, AgentReply, Conversation
from voxmail.domain.state_machine import ConversationState, is_final
from voxmail.llm.anthropic_client import AnthropicLLM
from voxmail.mail.sender import FakeMailSender

BUTTONS = {"1": Action.SEND, "2": Action.EDIT, "3": Action.CANCEL}
LABELS = {Action.SEND: "1) Envoyer", Action.EDIT: "2) Modifier", Action.CANCEL: "3) Annuler"}


def show(reply: AgentReply) -> None:
    print(f"\n🤖 {reply.text}")
    if reply.actions and reply.actions != [Action.CANCEL]:
        print("   " + "   ".join(LABELS[a] for a in reply.actions))
    print()


def wait_for_send(agent: Agent, conv: Conversation) -> None:
    """Countdown before sending. Pressing Enter cancels. (Works on macOS and Linux.)"""
    print("   ⏳ Appuyez sur Entrée pour annuler.")
    watch_input = True
    while conv.state == ConversationState.PENDING_SEND:
        # Wait up to 1 second for the user to press Enter.
        ready = select.select([sys.stdin], [], [], 1)[0] if watch_input else []
        if ready:
            if sys.stdin.readline():
                show(agent.handle_action(conv, Action.CANCEL))
                return
            watch_input = False  # input closed (e.g. piped): just wait
            time.sleep(1)
        if reply := agent.process_due_send(conv):
            show(reply)


def main() -> int:
    settings = get_settings()
    if settings.anthropic_api_key is None:
        print("❌ ANTHROPIC_API_KEY manquante. Ajoutez-la dans le fichier .env.")
        return 1

    sender = FakeMailSender()
    agent = Agent(
        llm=AnthropicLLM(settings.anthropic_api_key.get_secret_value(), settings.anthropic_model),
        contacts=JsonContactDirectory(settings.contacts_file),
        sender=sender,
        signature=settings.user_signature,
        send_delay=timedelta(seconds=settings.send_delay_seconds),
    )
    conv = agent.start()
    print("Voxmail (phase 1, envoi simulé). Dites-moi à qui écrire et quoi dire.")
    print("Tapez 'q' pour quitter.\n")

    while True:
        try:
            text = input("vous > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if text.lower() in {"q", "quit", "exit"}:
            return 0
        if not text:
            continue
        if is_final(conv.state):
            conv = agent.start()

        if conv.state == ConversationState.AWAITING_VALIDATION and text in BUTTONS:
            reply = agent.handle_action(conv, BUTTONS[text])
        else:
            reply = agent.handle_text(conv, text)
        show(reply)

        if conv.state == ConversationState.PENDING_SEND:
            wait_for_send(agent, conv)
            if conv.state == ConversationState.SENT:
                email = list(sender.sent.values())[-1]
                print(f"   [simulation] mail « {email.subject} » remis à {email.to}\n")


if __name__ == "__main__":
    sys.exit(main())
