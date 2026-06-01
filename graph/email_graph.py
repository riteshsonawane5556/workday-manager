import re
import warnings
from dataclasses import dataclass, field

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from agents.email_node import email_node_agent
from graph.pending_store import pending_store
from models.email_models import EmailMeta, EmailNodeOutput, ProcessingResult
from tools.email_tools import fetch_email_body, list_emails

_BODY_CHAR_LIMIT = 2000


def _clean_body(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:_BODY_CHAR_LIMIT]


@dataclass
class EmailPipelineState:
    emails: list[EmailMeta] = field(default_factory=list)
    current_index: int = 0
    outputs: list[EmailNodeOutput] = field(default_factory=list)
    pending_ids: list[str] = field(default_factory=list)


@dataclass
class FetchEmailsNode(BaseNode[EmailPipelineState]):
    n: int = 10

    async def run(self, ctx: GraphRunContext[EmailPipelineState]) -> "ClassifyNode":
        ctx.state.emails = await list_emails(self.n)
        ctx.state.current_index = 0
        return ClassifyNode()


@dataclass
class ClassifyNode(BaseNode[EmailPipelineState]):
    async def run(self, ctx: GraphRunContext[EmailPipelineState]) -> "DraftNode | End[ProcessingResult]":
        if ctx.state.current_index >= len(ctx.state.emails):
            return End(
                ProcessingResult(
                    processed=len(ctx.state.emails),
                    actionable=len(ctx.state.pending_ids),
                    pending_ids=ctx.state.pending_ids,
                )
            )
        email = ctx.state.emails[ctx.state.current_index]
        if pending_store.has_email(email.id):
            ctx.state.current_index += 1
            return ClassifyNode()
        body = _clean_body(await fetch_email_body(email.id))
        result = await email_node_agent.run(
            f"Email ID: {email.id}\nFrom: {email.sender}\n"
            f"Subject: {email.subject}\nDate: {email.date}\nBody:\n{body}"
        )
        output = result.output
        output.email_id = email.id
        output.subject = email.subject
        output.sender = email.sender
        ctx.state.outputs.append(output)
        return DraftNode()


@dataclass
class DraftNode(BaseNode[EmailPipelineState]):
    async def run(self, ctx: GraphRunContext[EmailPipelineState]) -> "HumanGateNode | ClassifyNode":
        output = ctx.state.outputs[-1]
        if output.classification.label == "actionable" and output.draft is not None:
            return HumanGateNode()
        ctx.state.current_index += 1
        return ClassifyNode()


@dataclass
class HumanGateNode(BaseNode[EmailPipelineState]):
    async def run(self, ctx: GraphRunContext[EmailPipelineState]) -> "ClassifyNode":
        output = ctx.state.outputs[-1]
        pending_id = pending_store.add(output)
        ctx.state.pending_ids.append(pending_id)
        ctx.state.current_index += 1
        return ClassifyNode()


with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    email_graph = Graph(
        nodes=(FetchEmailsNode, ClassifyNode, DraftNode, HumanGateNode),
        state_type=EmailPipelineState,
    )


async def run_email_pipeline(n: int = 10) -> ProcessingResult:
    state = EmailPipelineState()
    result = await email_graph.run(FetchEmailsNode(n=n), state=state)
    return result.output
