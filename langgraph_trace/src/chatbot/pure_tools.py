"""纯业务工具，使用装饰器自动追踪"""
from datetime import datetime
import random
from typing import List, Dict, Any
from langgraph_trace.src.tracing.decorators import trace_tool


class PureTools:
    @staticmethod
    @trace_tool("search_knowledge_base")
    def search_knowledge_base(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """搜索知识库"""
        return [
            {"title": f"知识{i+1}", "content": f"{query}相关内容{i+1}",
             "score": random.uniform(0.7, 0.99), "source": f"doc_{i+1}"}
            for i in range(min(top_k, 3))
        ]

    @staticmethod
    @trace_tool("get_current_time")
    def get_current_time() -> str:
        """获取当前时间"""
        return datetime.now().isoformat()

    @staticmethod
    @trace_tool("calculate")
    def calculate(expression: str) -> float:
        """安全计算器 - 仅支持基本数学运算"""
        import ast
        import operator

        # 定义安全的操作和常量
        safe_ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.Mod: operator.mod,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }

        safe_names = {"abs": abs, "round": round, "min": min, "max": max}

        def safe_eval(node):
            if isinstance(node, ast.Constant):  # Python 3.8+
                if isinstance(node.value, (int, float)):
                    return node.value
            elif isinstance(node, ast.BinOp):
                left = safe_eval(node.left)
                right = safe_eval(node.right)
                return safe_ops[type(node.op)](left, right)
            elif isinstance(node, ast.UnaryOp):
                operand = safe_eval(node.operand)
                return safe_ops[type(node.op)](operand)
            elif isinstance(node, ast.Name):
                if node.id in safe_names:
                    return safe_names[node.id]
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in safe_names:
                    args = [safe_eval(arg) for arg in node.args]
                    return safe_names[node.func.id](*args)
            raise ValueError(f"不支持的操作: {ast.dump(node)}")

        try:
            tree = ast.parse(expression, mode="eval")
            return safe_eval(tree.body)
        except Exception as e:
            raise ValueError(f"无效表达式: {expression}") from e

    @staticmethod
    @trace_tool("get_weather")
    def get_weather(city: str) -> Dict[str, Any]:
        """获取天气信息（模拟）"""
        return {
            "city": city,
            "temperature": random.randint(15, 35),
            "humidity": random.randint(40, 90),
            "condition": random.choice(["晴天","多云","小雨"]),
            "timestamp": datetime.now().isoformat()
        }
