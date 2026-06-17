"""
生成示例数据和初始化数据库的脚本
"""

import sys
import os
import random
from datetime import date, timedelta

# 添加src目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.connection import DatabaseConnection
from src.database.models import Product, SalesData, PredictionResult
from src.tools.lstm_predictor import generate_lstm_predictions


def create_sample_products() -> list:
    """创建示例产品数据"""
    products = [
        Product(
            product_code="P001",
            product_name="iPhone 15 Pro",
            category="智能手机",
            description="苹果旗舰智能手机"
        ),
        Product(
            product_code="P002",
            product_name="MacBook Pro 14",
            category="笔记本电脑",
            description="苹果专业笔记本电脑"
        ),
        Product(
            product_code="P003",
            product_name="AirPods Pro 2",
            category="耳机",
            description="苹果无线降噪耳机"
        ),
        Product(
            product_code="P004",
            product_name="iPad Air",
            category="平板电脑",
            description="苹果平板电脑"
        ),
        Product(
            product_code="P005",
            product_name="Apple Watch Series 9",
            category="智能手表",
            description="苹果智能手表"
        ),
        Product(
            product_code="P006",
            product_name="小米14 Ultra",
            category="智能手机",
            description="小米旗舰智能手机"
        ),
        Product(
            product_code="P007",
            product_name="华为Mate 60 Pro",
            category="智能手机",
            description="华为旗舰智能手机"
        ),
        Product(
            product_code="P008",
            product_name="戴森吹风机",
            category="个人护理",
            description="高端吹风机"
        ),
        Product(
            product_code="P009",
            product_name="Switch游戏机",
            category="游戏机",
            description="任天堂Switch游戏机"
        ),
        Product(
            product_code="P010",
            product_name="索尼PS5",
            category="游戏机",
            description="索尼PlayStation 5游戏机"
        )
    ]
    return products


def generate_sales_data(product_code: str, product_name: str, days: int = 90) -> list:
    """
    生成模拟销售数据

    Args:
        product_code: 产品代码
        product_name: 产品名称
        days: 生成天数

    Returns:
        销售数据列表
    """
    sales_data = []
    today = date.today()

    # 根据产品设置基础销量
    base_values = {
        "P001": 200,  # iPhone 高销量
        "P002": 80,
        "P003": 150,
        "P004": 100,
        "P005": 120,
        "P006": 180,
        "P007": 160,
        "P008": 50,
        "P009": 100,
        "P010": 60
    }

    base_value = base_values.get(product_code, 100)
    regions = ["华东", "华南", "华北", "华中", "西南"]

    for i in range(days):
        sale_date = today - timedelta(days=days - i - 1)

        # 工作日销量更高
        weekday_factor = 1.3 if sale_date.weekday() < 5 else 0.7

        # 模拟趋势（每周增长0.5%）
        trend = i * 0.5

        # 周末前略高
        if sale_date.weekday() == 4:  # 周五
            weekday_factor *= 1.2

        # 随机波动
        noise = random.uniform(0.85, 1.15)

        quantity = int((base_value + trend) * weekday_factor * noise)
        price = random.uniform(50, 5000)
        region = random.choice(regions)

        sales_data.append(SalesData(
            product_code=product_code,
            sale_date=sale_date,
            quantity=max(1, quantity),
            price=round(price, 2),
            region=region
        ))

    return sales_data


def generate_predictions(product_code: str, days: int = 90) -> list:
    """
    生成LSTM预测数据

    Args:
        product_code: 产品代码
        days: 天数

    Returns:
        预测数据列表
    """
    today = date.today()
    start_date = today - timedelta(days=days)

    return generate_lstm_predictions(product_code, start_date, today, base_value=100)


def init_database(config: dict = None):
    """
    初始化数据库并生成示例数据

    Args:
        config: 数据库配置
    """
    if config is None:
        config = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": "",
            "database": "prediction_db"
        }

    print("=" * 60)
    print("初始化数据库...")
    print("=" * 60)

    # 创建连接
    db = DatabaseConnection(**config)

    # 尝试连接或创建数据库
    try:
        if not db.connect():
            print("无法连接到数据库，请确保MySQL服务正在运行")
            print("将生成模拟数据用于测试")
            return None
    except Exception as e:
        print(f"连接数据库失败: {e}")
        print("将生成模拟数据用于测试")
        return None

    # 初始化表
    try:
        db.init_database()
        print("数据库表初始化完成")
    except Exception as e:
        print(f"初始化表失败: {e}")
        return None

    # 生成产品数据
    print("\n生成产品数据...")
    products = create_sample_products()

    for product in products:
        try:
            db.execute_update(
                """
                INSERT INTO products (product_code, product_name, category, description)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                product_name = VALUES(product_name),
                category = VALUES(category),
                description = VALUES(description)
                """,
                (product.product_code, product.product_name, product.category, product.description)
            )
            print(f"  - 添加产品: {product.product_name}")
        except Exception as e:
            print(f"  - 添加产品失败: {product.product_name}, {e}")

    # 生成销售数据和预测数据
    print("\n生成销售数据和预测数据...")
    for product in products:
        try:
            # 生成销售数据
            sales_data = generate_sales_data(product.product_code, product.product_name, days=90)

            for sale in sales_data:
                db.execute_update(
                    """
                    INSERT INTO sales_data (product_code, sale_date, quantity, price, region)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE quantity = VALUES(quantity)
                    """,
                    (sale.product_code, sale.sale_date, sale.quantity, sale.price, sale.region)
                )

            # 生成预测数据
            predictions = generate_predictions(product.product_code, days=90)

            for pred in predictions:
                db.execute_update(
                    """
                    INSERT INTO prediction_results
                    (product_code, prediction_date, predicted_value, confidence, model_type)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (pred["product_code"], pred["prediction_date"], pred["predicted_value"],
                     pred["confidence"], pred["model_type"])
                )

            print(f"  - 生成 {product.product_name} 的数据完成")

        except Exception as e:
            print(f"  - 生成数据失败: {product.product_name}, {e}")

    print("\n" + "=" * 60)
    print("数据库初始化完成！")
    print("=" * 60)

    return db


if __name__ == "__main__":
    init_database()
