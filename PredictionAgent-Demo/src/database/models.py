"""
数据模型定义
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, date


@dataclass
class Product:
    """产品模型"""
    id: Optional[int] = None
    product_code: str = ""
    product_name: str = ""
    category: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "product_code": self.product_code,
            "product_name": self.product_name,
            "category": self.category,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Product":
        return cls(
            id=data.get("id"),
            product_code=data.get("product_code", ""),
            product_name=data.get("product_name", ""),
            category=data.get("category"),
            description=data.get("description"),
            created_at=data.get("created_at")
        )


@dataclass
class SalesData:
    """销售数据模型"""
    id: Optional[int] = None
    product_code: str = ""
    sale_date: Optional[date] = None
    quantity: int = 0
    price: float = 0.0
    region: Optional[str] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "product_code": self.product_code,
            "sale_date": self.sale_date.isoformat() if self.sale_date else None,
            "quantity": self.quantity,
            "price": self.price,
            "region": self.region,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SalesData":
        sale_date = data.get("sale_date")
        if isinstance(sale_date, str):
            sale_date = datetime.strptime(sale_date, "%Y-%m-%d").date()
        return cls(
            id=data.get("id"),
            product_code=data.get("product_code", ""),
            sale_date=sale_date,
            quantity=data.get("quantity", 0),
            price=float(data.get("price", 0)),
            region=data.get("region"),
            created_at=data.get("created_at")
        )


@dataclass
class PredictionResult:
    """预测结果模型"""
    id: Optional[int] = None
    product_code: str = ""
    prediction_date: Optional[date] = None
    predicted_value: float = 0.0
    confidence: Optional[float] = None
    model_type: Optional[str] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "product_code": self.product_code,
            "prediction_date": self.prediction_date.isoformat() if self.prediction_date else None,
            "predicted_value": self.predicted_value,
            "confidence": self.confidence,
            "model_type": self.model_type,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PredictionResult":
        pred_date = data.get("prediction_date")
        if isinstance(pred_date, str):
            pred_date = datetime.strptime(pred_date, "%Y-%m-%d").date()
        return cls(
            id=data.get("id"),
            product_code=data.get("product_code", ""),
            prediction_date=pred_date,
            predicted_value=float(data.get("predicted_value", 0)),
            confidence=float(data.get("confidence", 0)) if data.get("confidence") else None,
            model_type=data.get("model_type"),
            created_at=data.get("created_at")
        )


@dataclass
class ProductAnalysisData:
    """产品分析综合数据"""
    product: Product
    sales_history: List[SalesData] = field(default_factory=list)
    model_predictions: List[PredictionResult] = field(default_factory=list)
    future_predictions: List[PredictionResult] = field(default_factory=list)

    def get_historical_dates(self) -> List[str]:
        """获取历史日期列表"""
        return [s.sale_date.isoformat() for s in sorted(self.sales_history, key=lambda x: x.sale_date)]

    def get_historical_values(self) -> List[float]:
        """获取历史销量列表"""
        sorted_sales = sorted(self.sales_history, key=lambda x: x.sale_date)
        return [s.quantity for s in sorted_sales]

    def get_model_predicted_values(self) -> List[float]:
        """获取模型预测值列表"""
        return [p.predicted_value for p in sorted(self.model_predictions, key=lambda x: x.prediction_date)]

    def get_future_dates(self) -> List[str]:
        """获取未来日期列表"""
        return [p.prediction_date.isoformat() for p in sorted(self.future_predictions, key=lambda x: x.prediction_date)]

    def get_future_predicted_values(self) -> List[float]:
        """获取未来预测值列表"""
        return [p.predicted_value for p in sorted(self.future_predictions, key=lambda x: x.prediction_date)]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "product": self.product.to_dict(),
            "sales_history": [s.to_dict() for s in self.sales_history],
            "model_predictions": [p.to_dict() for p in self.model_predictions],
            "future_predictions": [p.to_dict() for p in self.future_predictions]
        }
