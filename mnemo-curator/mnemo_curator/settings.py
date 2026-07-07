from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    github_token: str = ""
    github_repo: str = ""
    docs_root: str = ""

    mnemo_core_url: str = "http://localhost:7777"
    mnemo_api_token: str = ""
    mnemo_core_timeout_seconds: float = 120

    curator_stale_after_days: int = 180
    curator_max_files: int = 500
    curator_default_owner: str = "unset"
    curator_issue_tracker: Literal["github", "jira", "sqlite"] = "github"
    curator_issue_labels: str = "mnemo-curator"
    curator_issue_db_path: str = "./data/mnemo-curator-issues.db"
    curator_semantic_resolution_enabled: bool = False

    jira_base_url: str = ""
    jira_email: str = ""
    jira_api_token: str = ""
    jira_project_key: str = ""
    jira_issue_type: str = "Task"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    @property
    def issue_labels(self) -> list[str]:
        return [label.strip() for label in self.curator_issue_labels.split(",") if label.strip()]
