"""
AI問題自動生成システム
OpenAI API を使用して問題を自動生成する
"""

import json
import logging
import openai
from typing import Dict, Any, List, Optional
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Problem, Subject

User = get_user_model()
logger = logging.getLogger(__name__)

# OpenAI APIキーの設定
openai.api_key = getattr(settings, 'OPENAI_API_KEY', None)

class AIQuestionGenerator:
    """AI問題生成クラス"""
    
    def __init__(self):
        self.model = "gpt-3.5-turbo"
        self.max_tokens = 1000
        self.temperature = 0.7
    
    def generate_problem(
        self, 
        subject: Subject, 
        difficulty: str,
        problem_type: str = "multiple_choice",
        topic: Optional[str] = None,
        user_weaknesses: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        指定された条件で問題を生成
        
        Args:
            subject: 科目
            difficulty: 難易度 (easy, medium, hard)
            problem_type: 問題形式 (multiple_choice, essay, true_false)
            topic: 特定のトピック
            user_weaknesses: ユーザーの弱点領域
        
        Returns:
            生成された問題データ
        """
        try:
            if not openai.api_key:
                raise ValueError("OpenAI API key not configured")
            
            # プロンプトの構築
            prompt = self._build_prompt(
                subject=subject,
                difficulty=difficulty,
                problem_type=problem_type,
                topic=topic,
                user_weaknesses=user_weaknesses
            )
            
            # OpenAI API呼び出し
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "あなたは教育的な問題を作成する専門家です。日本語で高品質な学習問題を生成してください。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            # レスポンスの解析
            content = response.choices[0].message.content
            problem_data = json.loads(content)
            
            # データの検証と整形
            validated_data = self._validate_and_format_response(
                problem_data, 
                subject, 
                difficulty, 
                problem_type
            )
            
            return validated_data
            
        except Exception as e:
            logger.error(f"AI problem generation failed: {str(e)}")
            return self._get_fallback_problem(subject, difficulty, problem_type)
    
    def _build_prompt(
        self, 
        subject: Subject, 
        difficulty: str,
        problem_type: str,
        topic: Optional[str] = None,
        user_weaknesses: Optional[List[str]] = None
    ) -> str:
        """プロンプトを構築"""
        
        # 基本プロンプト
        prompt = f"""
以下の条件で学習問題を1つ生成してください：

**科目**: {subject.name}
**難易度**: {difficulty} (easy=初級, medium=中級, hard=上級)
**問題形式**: {problem_type}

"""
        
        # トピック指定
        if topic:
            prompt += f"**特定トピック**: {topic}\n"
        
        # 弱点領域への対応
        if user_weaknesses:
            prompt += f"**重点対策領域**: {', '.join(user_weaknesses)}\n"
        
        # 問題形式別の指示
        if problem_type == "multiple_choice":
            prompt += """
**要求事項**:
- 問題文は明確で理解しやすく
- 選択肢は4つ (A, B, C, D)
- 正解は1つのみ
- 間違いの選択肢も学習に役立つ内容
- 解説は詳細で教育的
"""
        elif problem_type == "essay":
            prompt += """
**要求事項**:
- 論述問題として適切な問題文
- 評価ポイントを明確に示す
- 模範解答例を提供
- 採点基準を含む
"""
        elif problem_type == "true_false":
            prompt += """
**要求事項**:
- 正誤判定問題として適切
- 明確な判断基準
- 詳細な解説
"""
        
        # JSON形式の指定
        prompt += """

**出力形式** (必ずJSON形式で出力):
```json
{
    "question": "問題文",
    "choices": ["選択肢A", "選択肢B", "選択肢C", "選択肢D"],
    "correct_answer": "正解の選択肢",
    "explanation": "詳細な解説",
    "keywords": ["関連キーワード1", "関連キーワード2"],
    "estimated_time_minutes": 予想解答時間（分）,
    "learning_objectives": ["学習目標1", "学習目標2"]
}
```

記述問題の場合:
```json
{
    "question": "問題文",
    "sample_answer": "模範解答例",
    "evaluation_points": ["評価ポイント1", "評価ポイント2"],
    "keywords": ["関連キーワード1", "関連キーワード2"],
    "estimated_time_minutes": 予想解答時間（分）,
    "learning_objectives": ["学習目標1", "学習目標2"]
}
```
"""
        
        return prompt
    
    def _validate_and_format_response(
        self, 
        problem_data: Dict[str, Any], 
        subject: Subject,
        difficulty: str,
        problem_type: str
    ) -> Dict[str, Any]:
        """AIレスポンスの検証と整形"""
        
        # 必須フィールドの確認
        required_fields = ["question", "keywords", "estimated_time_minutes", "learning_objectives"]
        
        if problem_type == "multiple_choice":
            required_fields.extend(["choices", "correct_answer", "explanation"])
        elif problem_type == "essay":
            required_fields.extend(["sample_answer", "evaluation_points"])
        
        for field in required_fields:
            if field not in problem_data:
                raise ValueError(f"Missing required field: {field}")
        
        # データの整形
        formatted_data = {
            "title": f"{subject.name} - {difficulty.capitalize()} Level Problem",
            "description": problem_data["question"],
            "problem_type": problem_type,
            "difficulty": difficulty,
            "subject": subject,
            "estimated_time_minutes": int(problem_data.get("estimated_time_minutes", 5)),
            "keywords": problem_data.get("keywords", []),
            "learning_objectives": problem_data.get("learning_objectives", []),
            "ai_generated": True,
            "ai_metadata": {
                "model": self.model,
                "temperature": self.temperature,
                "generation_timestamp": None  # 保存時に設定
            }
        }
        
        # 問題形式別のデータ追加
        if problem_type == "multiple_choice":
            formatted_data.update({
                "choices": problem_data["choices"],
                "correct_answer": problem_data["correct_answer"],
                "explanation": problem_data["explanation"]
            })
        elif problem_type == "essay":
            formatted_data.update({
                "sample_answer": problem_data["sample_answer"],
                "evaluation_points": problem_data["evaluation_points"]
            })
        elif problem_type == "true_false":
            formatted_data.update({
                "correct_answer": problem_data.get("correct_answer", "True"),
                "explanation": problem_data.get("explanation", "")
            })
        
        return formatted_data
    
    def _get_fallback_problem(
        self, 
        subject: Subject, 
        difficulty: str, 
        problem_type: str
    ) -> Dict[str, Any]:
        """AI生成失敗時のフォールバック問題"""
        
        fallback_problems = {
            "multiple_choice": {
                "question": f"{subject.name}に関する基本的な問題です。",
                "choices": ["選択肢A", "選択肢B", "選択肢C", "選択肢D"],
                "correct_answer": "選択肢A",
                "explanation": "この問題はAI生成に失敗したため、フォールバック問題として提供されています。",
                "keywords": [subject.name, "基本"],
                "estimated_time_minutes": 3,
                "learning_objectives": [f"{subject.name}の基本理解"]
            },
            "essay": {
                "question": f"{subject.name}について説明してください。",
                "sample_answer": f"{subject.name}の概要について記述する。",
                "evaluation_points": ["正確性", "論理性", "完全性"],
                "keywords": [subject.name],
                "estimated_time_minutes": 10,
                "learning_objectives": [f"{subject.name}の理解と表現力"]
            }
        }
        
        base_data = fallback_problems.get(problem_type, fallback_problems["multiple_choice"])
        
        return {
            "title": f"{subject.name} - フォールバック問題",
            "description": base_data["question"],
            "problem_type": problem_type,
            "difficulty": difficulty,
            "subject": subject,
            "ai_generated": False,
            "fallback": True,
            **base_data
        }
    
    def generate_batch_problems(
        self, 
        subject: Subject,
        count: int = 5,
        difficulty_distribution: Optional[Dict[str, int]] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        複数の問題を一括生成
        
        Args:
            subject: 科目
            count: 生成する問題数
            difficulty_distribution: 難易度別の問題数 {"easy": 2, "medium": 2, "hard": 1}
            user_preferences: ユーザーの学習傾向
        
        Returns:
            生成された問題のリスト
        """
        
        if not difficulty_distribution:
            # デフォルトの難易度分布
            difficulty_distribution = {
                "easy": count // 3,
                "medium": count // 3,
                "hard": count - (2 * (count // 3))
            }
        
        problems = []
        
        for difficulty, num_problems in difficulty_distribution.items():
            for i in range(num_problems):
                try:
                    problem_data = self.generate_problem(
                        subject=subject,
                        difficulty=difficulty,
                        problem_type="multiple_choice",  # デフォルト
                        user_weaknesses=user_preferences.get("weaknesses", []) if user_preferences else None
                    )
                    problems.append(problem_data)
                    
                except Exception as e:
                    logger.error(f"Failed to generate problem {i+1} for {difficulty}: {str(e)}")
                    # フォールバック問題を追加
                    fallback = self._get_fallback_problem(subject, difficulty, "multiple_choice")
                    problems.append(fallback)
        
        return problems
    
    def generate_adaptive_problem(
        self, 
        user: User,
        subject: Subject,
        recent_performance: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        ユーザーの学習履歴に基づいてパーソナライズされた問題を生成
        
        Args:
            user: ユーザー
            subject: 科目
            recent_performance: 最近のパフォーマンス分析
        
        Returns:
            パーソナライズされた問題
        """
        
        # ユーザーの弱点分析
        weaknesses = []
        difficulty = "medium"  # デフォルト
        
        if recent_performance:
            # パフォーマンスに基づく難易度調整
            accuracy = recent_performance.get("accuracy", 0.7)
            if accuracy > 0.8:
                difficulty = "hard"
            elif accuracy < 0.6:
                difficulty = "easy"
            
            # 弱点領域の特定
            weaknesses = recent_performance.get("weak_topics", [])
        
        return self.generate_problem(
            subject=subject,
            difficulty=difficulty,
            user_weaknesses=weaknesses
        )