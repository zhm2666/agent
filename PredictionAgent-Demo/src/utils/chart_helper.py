"""
图表绘制辅助类
"""

import os
from typing import List, Dict, Any, Optional
import matplotlib
matplotlib.use('Agg')  # 非交互式后端
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import uuid


class ChartHelper:
    """图表绘制辅助类"""

    def __init__(self, output_dir: str = "output/charts"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_chart_id(self) -> str:
        """生成唯一图表ID"""
        return uuid.uuid4().hex[:8]

    def plot_sales_forecast(
        self,
        product_name: str,
        dates: List[str],
        actual_values: List[float],
        predicted_values: List[float],
        future_dates: List[str],
        future_predictions: List[float],
        chart_type: str = "combined"
    ) -> Dict[str, Any]:
        """
        绘制销量预测图表

        Args:
            product_name: 产品名称
            dates: 历史日期列表
            actual_values: 历史真实值
            predicted_values: 模型预测值
            future_dates: 未来日期列表
            future_predictions: 未来预测值
            chart_type: 图表类型 (bar/line/combined)

        Returns:
            包含图表路径和URL的字典
        """
        chart_id = self.generate_chart_id()

        if chart_type == "bar":
            return self._plot_bar_chart(
                product_name, dates, actual_values, predicted_values,
                future_dates, future_predictions, chart_id
            )
        elif chart_type == "line":
            return self._plot_line_chart(
                product_name, dates, actual_values, predicted_values,
                future_dates, future_predictions, chart_id
            )
        else:  # combined
            return self._plot_combined_chart(
                product_name, dates, actual_values, predicted_values,
                future_dates, future_predictions, chart_id
            )

    def _plot_bar_chart(
        self, product_name: str, dates: List[str], actual_values: List[float],
        predicted_values: List[float], future_dates: List[str],
        future_predictions: List[float], chart_id: str
    ) -> Dict[str, Any]:
        """绘制柱状图"""
        fig, ax = plt.subplots(figsize=(14, 6))

        # 合并所有日期和值
        all_dates = dates + future_dates
        all_actual = actual_values + [0] * len(future_dates)
        all_predicted = predicted_values + future_predictions
        all_future_actual = [0] * len(dates) + [None] * len(future_dates)

        x = range(len(all_dates))
        width = 0.35

        # 柱状图
        bars1 = ax.bar([i - width/2 for i in x], all_actual, width,
                       label='实际销量', color='#2ecc71', alpha=0.8)
        bars2 = ax.bar([i + width/2 for i in x], all_predicted, width,
                       label='预测销量', color='#3498db', alpha=0.8)

        # 添加分隔线
        ax.axvline(x=len(dates) - 0.5, color='red', linestyle='--',
                   linewidth=2, label='预测分界线')

        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('销量', fontsize=12)
        ax.set_title(f'{product_name} - 销量预测分析 (柱状图)', fontsize=14, fontweight='bold')
        ax.set_xticks(x[::max(1, len(x)//10)])
        ax.set_xticklabels([all_dates[i] for i in range(0, len(all_dates), max(1, len(all_dates)//10))],
                          rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()

        filename = f"sales_forecast_{chart_id}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        return {
            "filepath": filepath,
            "url": f"/charts/{filename}",
            "chart_id": chart_id,
            "chart_type": "bar"
        }

    def _plot_line_chart(
        self, product_name: str, dates: List[str], actual_values: List[float],
        predicted_values: List[float], future_dates: List[str],
        future_predictions: List[float], chart_id: str
    ) -> Dict[str, Any]:
        """绘制折线图"""
        fig, ax = plt.subplots(figsize=(14, 6))

        # 转换日期
        all_dates = [datetime.strptime(d, '%Y-%m-%d') for d in dates + future_dates]

        # 历史数据
        hist_dates = all_dates[:len(dates)]
        future_all_dates = all_dates[len(dates):]

        # 绘制折线
        ax.plot(hist_dates, actual_values, 'g-o', linewidth=2,
                markersize=6, label='实际销量', color='#2ecc71')
        ax.plot(hist_dates, predicted_values, 'b--s', linewidth=2,
                markersize=5, label='模型预测', color='#3498db')
        ax.plot(future_all_dates, future_predictions, 'r-^', linewidth=2,
                markersize=6, label='未来预测', color='#e74c3c')

        # 添加分隔线
        ax.axvline(x=hist_dates[-1], color='red', linestyle='--',
                   linewidth=2, label='预测分界线')

        # 填充预测区间
        ax.fill_between(future_all_dates,
                       [p * 0.9 for p in future_predictions],
                       [p * 1.1 for p in future_predictions],
                       alpha=0.2, color='#e74c3c', label='预测置信区间(±10%)')

        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('销量', fontsize=12)
        ax.set_title(f'{product_name} - 销量预测分析 (折线图)', fontsize=14, fontweight='bold')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        plt.xticks(rotation=45, ha='right')
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        filename = f"sales_forecast_{chart_id}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        return {
            "filepath": filepath,
            "url": f"/charts/{filename}",
            "chart_id": chart_id,
            "chart_type": "line"
        }

    def _plot_combined_chart(
        self, product_name: str, dates: List[str], actual_values: List[float],
        predicted_values: List[float], future_dates: List[str],
        future_predictions: List[float], chart_id: str
    ) -> Dict[str, Any]:
        """绘制组合图表（柱状图+折线图）"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10),
                                        gridspec_kw={'height_ratios': [2, 1]})

        all_dates = dates + future_dates
        all_dates_dt = [datetime.strptime(d, '%Y-%m-%d') for d in all_dates]
        x = range(len(all_dates))

        # 上图：柱状图
        width = 0.4
        ax1.bar([i - width/2 for i in x[:len(dates)]], actual_values, width,
                label='实际销量', color='#2ecc71', alpha=0.8)
        ax1.bar([i + width/2 for i in x[:len(dates)]], predicted_values[:len(dates)], width,
                label='模型预测', color='#3498db', alpha=0.8)
        ax1.bar([i for i in x[len(dates):]], future_predictions, width,
                label='未来预测', color='#e74c3c', alpha=0.8)

        ax1.axvline(x=len(dates) - 0.5, color='red', linestyle='--',
                    linewidth=2, label='预测分界线')
        ax1.set_ylabel('销量', fontsize=12)
        ax1.set_title(f'{product_name} - 销量预测综合分析', fontsize=14, fontweight='bold')
        ax1.set_xticks(x[::max(1, len(x)//8)])
        ax1.set_xticklabels([all_dates[i] for i in range(0, len(all_dates), max(1, len(all_dates)//8))],
                            rotation=45, ha='right')
        ax1.legend(loc='upper left')
        ax1.grid(axis='y', alpha=0.3)

        # 下图：误差分析
        errors = [actual_values[i] - predicted_values[i]
                  for i in range(min(len(actual_values), len(predicted_values)))]
        colors = ['#2ecc71' if e >= 0 else '#e74c3c' for e in errors]
        ax2.bar(range(len(errors)), errors, color=colors, alpha=0.8)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax2.set_xlabel('时间序列', fontsize=12)
        ax2.set_ylabel('预测误差', fontsize=12)
        ax2.set_title('预测误差分析 (实际值 - 预测值)', fontsize=12)
        ax2.grid(axis='y', alpha=0.3)

        # 计算MAPE
        mape = sum(abs(actual_values[i] - predicted_values[i]) / actual_values[i]
                   for i in range(len(actual_values))) / len(actual_values) * 100
        ax2.text(0.02, 0.95, f'MAPE: {mape:.2f}%', transform=ax2.transAxes,
                fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()

        filename = f"sales_forecast_{chart_id}.png"
        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()

        return {
            "filepath": filepath,
            "url": f"/charts/{filename}",
            "chart_id": chart_id,
            "chart_type": "combined"
        }
