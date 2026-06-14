class PipelineError(Exception):
    pass


class ProcessingError(PipelineError):
    """LLM returned an invalid or unparseable response."""
    pass


class PublishError(PipelineError):
    """GitHub API call failed during commit or PR creation."""
    pass
