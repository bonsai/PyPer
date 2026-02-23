"""
Gemini APIを使った論文要約生成モジュール
Structured Outputsで確実に指定形式の出力を取得
"""

import google.generativeai as genai
from pydantic import BaseModel, Field, ValidationError
import logging
from typing import Optional, List
import json
from datetime import datetime
import asyncio
from PIL import Image
import requests
from io import BytesIO

logger = logging.getLogger(__name__)

# 構造化出力のためのスキーマ定義
class PaperSummary(BaseModel):
    """論文要約の構造化データ"""
    # X用（140字制限）
    x_summary: str = Field(
        description="X（Twitter）用の140字以内の要約。簡潔で印象に残る表現で。",
        max_length=140
    )
    
    # ブログ用（800字程度）
    blog_summary: str = Field(
        description="ブログ用の800字程度の詳細な要約。研究の背景、手法、結果、意義を含めて。",
        max_length=1000  # 少し余裕を持たせる
    )
    
    # キーワード（ハッシュタグ用）
    keywords: List[str] = Field(
        description="5つ以内の重要キーワード",
        max_items=5
    )
    
    # 研究のカテゴリ
    category: str = Field(
        description="研究カテゴリ（例： neuroscience, AI, physics, biology など）"
    )
    
    # インパクトレベル（一般読者向けの分かりやすさ）
    impact_level: int = Field(
        description="一般読者への分かりやすさ（1-5、5が最も分かりやすい）",
        ge=1,
        le=5
    )

class PaperSummarizer:
    """Gemini APIを使った論文要約生成クラス"""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-exp"):
        """
        初期化
        
        Args:
            api_key: Gemini API Key
            model_name: 使用するモデル名
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name
        
        # 日本語プロンプトの最適化設定
        self.generation_config = {
            "temperature": 0.3,  # 低めにして一貫性を確保
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 2048,
        }
        
    def _create_prompt(self, paper_title: str, paper_summary: str, 
                      pdf_content: Optional[str] = None) -> str:
        """
        論文要約のためのプロンプトを作成
        
        Args:
            paper_title: 論文タイトル
            paper_summary: 論文の概要（RSSのsummary）
            pdf_content: PDFから抽出したテキスト（任意）
            
        Returns:
            プロンプト文字列
        """
        prompt = f"""あなたは学術論文を一般向けに解説するサイエンスコミュニケーターです。
以下の論文を読んで、指定された形式で要約を生成してください。

## 論文タイトル
{paper_title}

## 論文概要
{paper_summary}

"""

        if pdf_content:
            prompt += f"""
## PDFから抽出した内容
{pdf_content[:3000]}  # 長すぎる場合は制限
"""
        
        prompt += """
## 出力形式（厳守）
以下のJSON形式で必ず出力してください：

{
    "x_summary": "140字以内のX用要約（簡潔で印象的に）",
    "blog_summary": "800字程度のブログ用要約（背景・手法・結果・意義を詳しく）",
    "keywords": ["キーワード1", "キーワード2", "キーワード3", "キーワード4", "キーワード5"],
    "category": "研究カテゴリ",
    "impact_level": 3
}

## 要約のポイント
1. X用（140字）：研究の核心を一言で！一般人の興味を引く工夫を
2. ブログ用（800字）：
   - 研究の背景（なぜこの研究が重要か）
   - 手法（どうやって調べたか）
   - 主な発見（何がわかったか）
   - 社会的意義（私たちの生活にどう関係するか）
3. キーワード：ハッシュタグに使えるものを5つ
4. カテゴリ：分野を1語で
5. インパクトレベル：1（専門家向け）〜5（小学生でも理解できる）

必ず有効なJSON形式で出力してください。説明文は不要です。
"""
        return prompt
    
    def _download_pdf_content(self, pdf_url: str) -> Optional[str]:
        """
        PDFをダウンロードしてテキスト抽出（簡易版）
        実際の運用では、PyPDF2やpdfplumberなどのライブラリを使用
        
        Args:
            pdf_url: PDFのURL
            
        Returns:
            抽出したテキスト（またはNone）
        """
        try:
            # 注意: これは簡易実装です
            # 実際のPDF解析には別途ライブラリが必要
            response = requests.get(pdf_url, timeout=10)
            if response.status_code == 200:
                # ここではPDF解析は省略
                # 代わりにURLを返す（次のフェーズで実装）
                return f"[PDF from {pdf_url}]"
            return None
        except Exception as e:
            logger.warning(f"PDF download failed: {e}")
            return None
    
    def _download_figure(self, paper_url: str) -> Optional[Image.Image]:
        """
        論文のフィギュアをダウンロード（Natureの場合）
        実際の運用では、論文ページからメインフィギュアを抽出
        
        Args:
            paper_url: 論文URL
            
        Returns:
            PIL Image（またはNone）
        """
        try:
            # Natureの場合、サムネイルが存在することが多い
            if 'nature.com' in paper_url:
                # 記事IDを抽出
                article_id = paper_url.split('/articles/')[-1]
                # サムネイルURLの推測
                thumbnail_url = f"https://media.springernature.com/full/springer-static/image/art%3A10.1038%2F{article_id}/MediaObjects/41586_{article_id}_Fig1_HTML.png"
                
                response = requests.get(thumbnail_url, timeout=10)
                if response.status_code == 200:
                    return Image.open(BytesIO(response.content))
            return None
        except Exception as e:
            logger.warning(f"Figure download failed: {e}")
            return None
    
    def generate_summary(self, paper_title: str, paper_summary: str, 
                        paper_url: str = None) -> Optional[PaperSummary]:
        """
        論文要約を生成
        
        Args:
            paper_title: 論文タイトル
            paper_summary: 論文概要
            paper_url: 論文URL（PDF/図表取得用）
            
        Returns:
            PaperSummaryオブジェクト（失敗時はNone）
        """
        try:
            # 図表の取得（マルチモーダル入力用）
            images = []
            if paper_url:
                figure = self._download_figure(paper_url)
                if figure:
                    images.append(figure)
                    logger.info("✓ 図表を取得しました")
            
            # PDF内容の取得（実際には非同期処理推奨）
            pdf_content = None
            # TODO: PDF解析の実装
            
            # プロンプト作成
            prompt = self._create_prompt(paper_title, paper_summary, pdf_content)
            
            # API呼び出し（マルチモーダル対応）
            if images:
                # 画像ありの場合
                response = self.model.generate_content(
                    [prompt] + images,
                    generation_config=self.generation_config
                )
            else:
                # テキストのみの場合
                response = self.model.generate_content(
                    prompt,
                    generation_config=self.generation_config
                )
            
            # レスポンスの解析
            if not response.text:
                logger.error("Empty response from Gemini API")
                return None
            
            # JSONの抽出（応答テキストからJSON部分を抽出）
            json_str = self._extract_json(response.text)
            if not json_str:
                logger.error(f"Failed to extract JSON from response: {response.text[:200]}")
                return None
            
            # JSONのパースとバリデーション
            try:
                data = json.loads(json_str)
                summary = PaperSummary(**data)
                
                # 文字数制限の確認
                if len(summary.x_summary) > 140:
                    logger.warning(f"X summary too long ({len(summary.x_summary)} chars), truncating...")
                    summary.x_summary = summary.x_summary[:137] + "..."
                
                logger.info(f"✓ 要約生成成功: {summary.category} (影響度: {summary.impact_level}/5)")
                return summary
                
            except ValidationError as e:
                logger.error(f"Validation error: {e}")
                return None
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None
    
    def _extract_json(self, text: str) -> Optional[str]:
        """
        応答テキストからJSON部分を抽出
        
        Args:
            text: 応答テキスト
            
        Returns:
            JSON文字列（またはNone）
        """
        # コードブロックで囲まれている場合
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        
        # ``` だけの場合
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()
        
        # { で始まり } で終わる部分を探す
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            return text[start:end]
        
        return None
    
    async def generate_summary_async(self, paper_title: str, paper_summary: str,
                                     paper_url: str = None) -> Optional[PaperSummary]:
        """
        非同期版の要約生成
        
        Args:
            同上
        """
        return await asyncio.to_thread(
            self.generate_summary,
            paper_title,
            paper_summary,
            paper_url
        )

# バッチ処理用のユーティリティ
class BatchSummarizer:
    """複数論文の一括要約"""
    
    def __init__(self, summarizer: PaperSummarizer):
        self.summarizer = summarizer
    
    async def process_batch(self, papers: List[dict]) -> List[tuple]:
        """
        複数論文を非同期で処理
        
        Args:
            papers: 論文情報のリスト
            
        Returns:
            (論文, 要約)のタプルリスト
        """
        tasks = []
        for paper in papers:
            task = self.summarizer.generate_summary_async(
                paper['title'],
                paper['summary'],
                paper.get('url')
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果の整形
        processed = []
        for paper, result in zip(papers, results):
            if isinstance(result, Exception):
                logger.error(f"Failed to process {paper['title']}: {result}")
                processed.append((paper, None))
            else:
                processed.append((paper, result))
        
        return processed