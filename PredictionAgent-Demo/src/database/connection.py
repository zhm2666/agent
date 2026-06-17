"""
MySQL数据库连接管理
"""

import mysql.connector
from mysql.connector import Error
from typing import Optional, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseConnection:
    """MySQL数据库连接管理器"""

    _instance = None

    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None

    @classmethod
    def get_instance(cls, config: Optional[Dict[str, Any]] = None) -> "DatabaseConnection":
        """获取单例实例"""
        if cls._instance is None:
            if config is None:
                raise ValueError("首次创建需要提供数据库配置")
            cls._instance = cls(
                host=config.get("host", "localhost"),
                port=config.get("port", 3306),
                user=config.get("user", "root"),
                password=config.get("password", ""),
                database=config.get("database", "prediction_db")
            )
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """重置单例（用于测试或切换数据库）"""
        if cls._instance and cls._instance.connection:
            cls._instance.connection.close()
        cls._instance = None

    def connect(self) -> bool:
        """建立数据库连接"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            logger.info(f"成功连接到数据库: {self.database}")
            return True
        except Error as e:
            logger.error(f"数据库连接失败: {e}")
            return False

    def get_connection(self):
        """获取连接对象"""
        if self.connection is None or not self.connection.is_connected():
            self.connect()
        return self.connection

    def execute_query(self, query: str, params: tuple = None) -> list:
        """执行查询"""
        try:
            connection = self.get_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            cursor.close()
            return result
        except Error as e:
            logger.error(f"查询执行失败: {e}")
            raise e

    def execute_update(self, query: str, params: tuple = None) -> int:
        """执行更新操作"""
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(query, params or ())
            connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected
        except Error as e:
            logger.error(f"更新执行失败: {e}")
            raise e

    def execute_many(self, query: str, data_list: list) -> int:
        """批量执行"""
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.executemany(query, data_list)
            connection.commit()
            affected = cursor.rowcount
            cursor.close()
            return affected
        except Error as e:
            logger.error(f"批量执行失败: {e}")
            raise e

    def close(self):
        """关闭连接"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("数据库连接已关闭")

    def init_database(self):
        """初始化数据库表"""
        create_products_table = """
        CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_code VARCHAR(50) UNIQUE NOT NULL,
            product_name VARCHAR(200) NOT NULL,
            category VARCHAR(100),
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """

        create_sales_table = """
        CREATE TABLE IF NOT EXISTS sales_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_code VARCHAR(50) NOT NULL,
            sale_date DATE NOT NULL,
            quantity INT NOT NULL,
            price DECIMAL(10, 2),
            region VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_code) REFERENCES products(product_code),
            UNIQUE KEY unique_sale (product_code, sale_date, region)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """

        create_predictions_table = """
        CREATE TABLE IF NOT EXISTS prediction_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_code VARCHAR(50) NOT NULL,
            prediction_date DATE NOT NULL,
            predicted_value DECIMAL(10, 2) NOT NULL,
            confidence DECIMAL(5, 2),
            model_type VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_code) REFERENCES products(product_code)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """

        try:
            self.execute_update(create_products_table)
            self.execute_update(create_sales_table)
            self.execute_update(create_predictions_table)
            logger.info("数据库表初始化完成")
        except Error as e:
            logger.error(f"表初始化失败: {e}")
            raise e
