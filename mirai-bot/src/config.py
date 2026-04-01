from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    """環境変数から設定を読み込む"""
    
    # RSSフィード
    rss_url: str = Field("https://www.nature.com/nature.rss", description="NatureのRSS URL")
    
    # Gemini API
    gemini_api_key: Optional[str] = Field(None, description="Gemini API Key")
    gemini_model: str = Field("gemini-2.0-flash-exp", description="使用するGeminiモデル")
    
    # はてなブログ
    hatena_blog_id: Optional[str] = Field(None, description="はてなブログID")
    hatena_api_key: Optional[str] = Field(None, description="はてなAPIキー")
    hatena_blog_url: Optional[str] = Field(None, description="はてなブログのAtomPub URL")
    
    # X (Twitter) API
    x_api_key: Optional[str] = Field(None, description="X API Key")
    x_api_secret: Optional[str] = Field(None, description="X API Secret")
    x_access_token: Optional[str] = Field(None, description="X Access Token")
    x_access_token_secret: Optional[str] = Field(None, description="X Access Token Secret")
    
    # データ保存
    data_dir: str = Field("data", description="データ保存ディレクトリ")
    seen_urls_file: str = Field("seen_urls.txt", description="既読URL保存ファイル")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# グローバルな設定インスタンス
settings = Settings()