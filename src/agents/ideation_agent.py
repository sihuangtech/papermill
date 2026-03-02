import os
import json
import logging
import yaml
import arxiv
import requests
from scholarly import scholarly
from huggingface_hub import HfApi
from github import Github
from typing import List, Dict
from .llm_client import call_llm

class IdeationAgent:
    def __init__(self, config_path: str, prompts_path: str = "prompts.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        with open(prompts_path, 'r', encoding='utf-8') as f:
            self.prompts = yaml.safe_load(f)['ideation']
        self.logger = logging.getLogger(__name__)
        self.memory_path = "src/workspace/memory/processed_papers.json"
        self._load_memory()

    def _load_memory(self):
        if os.path.exists(self.memory_path):
            with open(self.memory_path, 'r', encoding='utf-8') as f:
                self.processed_papers = json.load(f)
        else:
            self.processed_papers = []

    def _save_memory(self):
        with open(self.memory_path, 'w', encoding='utf-8') as f:
            json.dump(self.processed_papers, f, indent=4)

    def search_literature(self, query: str) -> List[Dict]:
        """检索相关文献和项目"""
        results = []

        # arXiv 检索
        self.logger.info(f"正在从 arXiv 检索: {query}")
        search = arxiv.Search(query=query, max_results=5, sort_by=arxiv.SortCriterion.Relevance)
        for result in search.results():
            if result.entry_id not in self.processed_papers:
                results.append({
                    'source': 'arXiv',
                    'id': result.entry_id,
                    'title': result.title,
                    'summary': result.summary,
                    'url': result.pdf_url
                })
                self.processed_papers.append(result.entry_id)

        # Semantic Scholar 简易检索 (使用 requests)
        try:
            ss_url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=5&fields=title,abstract,url"
            response = requests.get(ss_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for item in data.get('data', []):
                    results.append({
                        'source': 'Semantic Scholar',
                        'title': item.get('title'),
                        'summary': item.get('abstract'),
                        'url': item.get('url')
                    })
        except Exception as e:
            self.logger.error(f"Semantic Scholar 检索失败: {e}")

        # Google Scholar 检索 (使用 scholarly)
        try:
            self.logger.info(f"正在从 Google Scholar 检索: {query}")
            search_query = scholarly.search_pubs(query)
            for i, pub in enumerate(search_query):
                if i >= 3: break
                bib = pub.get('bib', {})
                results.append({
                    'source': 'Google Scholar',
                    'title': bib.get('title'),
                    'summary': bib.get('abstract'),
                    'url': pub.get('pub_url')
                })
        except Exception as e:
            self.logger.error(f"Google Scholar 检索失败: {e}")

        # HuggingFace 检索
        try:
            self.logger.info(f"正在从 HuggingFace 检索: {query}")
            api = HfApi()
            models = api.list_models(search=query, sort="downloads", direction=-1, limit=3)
            for model in models:
                results.append({
                    'source': 'HuggingFace',
                    'title': model.modelId,
                    'summary': f"Downloads: {model.downloads}",
                    'url': f"https://huggingface.co/{model.modelId}"
                })
        except Exception as e:
            self.logger.error(f"HuggingFace 检索失败: {e}")

        # GitHub 检索
        try:
            self.logger.info(f"正在从 GitHub 检索: {query}")
            g = Github(os.getenv("GITHUB_TOKEN"))
            repositories = g.search_repositories(query=f"{query} language:python", sort="stars", order="desc")
            for i, repo in enumerate(repositories):
                if i >= 3: break
                results.append({
                    'source': 'GitHub',
                    'title': repo.full_name,
                    'summary': repo.description,
                    'url': repo.html_url
                })
        except Exception as e:
            self.logger.error(f"GitHub 检索失败: {e}")

        self._save_memory()
        return results

    def generate_ideas(self) -> List[Dict]:
        """生成研究假设"""
        directions = self.config.get('research_directions', [])
        all_ideas = []

        for direction in directions:
            literature = self.search_literature(direction)
            context_list = []
            for l in literature:
                summary = l.get('summary') or ""
                context_list.append(f"- {l['source']}: {l['title']} ({summary[:200]}...)")
            context = "\n".join(context_list)

            prompt = self.prompts['generate_ideas'].format(
                max_ideas=self.config.get('max_ideas_per_cycle', 5),
                direction=direction,
                context=context
            )
            try:
                response = call_llm(prompt, model=self.config.get('llm_model', 'gpt-4o'))
                # 提取 JSON 部分
                if "```json" in response:
                    response = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    response = response.split("```")[1].split("```")[0].strip()

                ideas = json.loads(response)
                for idea in ideas:
                    score = self.review_idea(idea)
                    if score >= self.config.get('hypothesis_review_threshold', 6):
                        idea['score'] = score
                        all_ideas.append(idea)
                        self._save_idea_to_file(idea)
            except Exception as e:
                self.logger.error(f"生成假设失败 ({direction}): {e}")

        return all_ideas

    def review_idea(self, idea: Dict) -> int:
        """对想法进行自我打分"""
        prompt = self.prompts['review_idea'].format(
            title=idea.get('title'),
            problem_statement=idea.get('Problem Statement'),
            core_hypothesis=idea.get('Core Hypothesis'),
            proposed_verification=idea.get('Proposed Verification')
        )
        try:
            score_str = call_llm(prompt, model=self.config.get('llm_model', 'gpt-4o'), max_tokens=10).strip()
            return int(''.join(filter(str.isdigit, score_str)))
        except:
            return 0

    def _save_idea_to_file(self, idea: Dict):
        idea_id = idea.get('title', 'untitled').replace(' ', '_').lower()
        filepath = f"src/workspace/ideas/idea_{idea_id}.md"
        content = f"""# {idea.get('title')}

## 问题陈述
{idea.get('Problem Statement')}

## 核心假设
{idea.get('Core Hypothesis')}

## 预期验证方式
{idea.get('Proposed Verification')}

## 创新点
{idea.get('Novelty')}

## 评分: {idea.get('score')}
"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        self.logger.info(f"已保存想法: {filepath}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = IdeationAgent("config.yaml")
    agent.generate_ideas()
