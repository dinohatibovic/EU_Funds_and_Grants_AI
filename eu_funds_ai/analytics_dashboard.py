FinAssist BH - Analytics and Reporting Dashboard
Napredni sistem za analitiku, izvještavanje i vizualizaciju podataka
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ReportType(Enum):
    """Tipovi izvještaja"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    CUSTOM = "custom"

class MetricType(Enum):
    """Tipovi metrika"""
    GRANTS_COUNT = "grants_count"
    USER_ACTIVITY = "user_activity"
    SUBSCRIPTION_REVENUE = "subscription_revenue"
    ELIGIBILITY_SCORES = "eligibility_scores"
    CONVERSION_RATES = "conversion_rates"
    GEOGRAPHIC_DISTRIBUTION = "geographic_distribution"
    CATEGORY_POPULARITY = "category_popularity"
    SUCCESS_RATES = "success_rates"

@dataclass
class AnalyticsData:
    """Podaci za analitiku"""
    metric_type: MetricType
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    dimensions: Dict[str, str] = field(default_factory=dict)

@dataclass
class DashboardWidget:
    """Widget za dashboard"""
    widget_id: str
    title: str
    widget_type: str  # chart, table, metric, map
    data_source: str
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, int] = field(default_factory=dict)  # x, y, width, height
    is_active: bool = True

class FinAssistAnalyticsDashboard:
    """Glavni sistem za analitiku i dashboard"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.analytics_data: List[AnalyticsData] = []
        self.widgets: List[DashboardWidget] = []
        self.cached_reports: Dict[str, Any] = {}
        
        # Inicijaliziraj osnovne widget-e
        self._initialize_default_widgets()
        
    def _initialize_default_widgets(self):
        """Inicijalizuje osnovne widget-e"""
        default_widgets = [
            DashboardWidget(
                widget_id="grants_overview",
                title="Pregled Grantova",
                widget_type="metric",
                data_source="grants_count",
                position={"x": 0, "y": 0, "width": 3, "height": 2}
            ),
            DashboardWidget(
                widget_id="user_growth",
                title="Rast Korisnika",
                widget_type="chart",
                data_source="user_activity",
                config={"chart_type": "line"},
                position={"x": 3, "y": 0, "width": 6, "height": 4}
            ),
            DashboardWidget(
                widget_id="revenue_chart",
                title="Prihodi po Mjesecima",
                widget_type="chart",
                data_source="subscription_revenue",
                config={"chart_type": "bar"},
                position={"x": 9, "y": 0, "width": 3, "height": 4}
            ),
            DashboardWidget(
                widget_id="geographic_map",
                title="Geografska Distribucija",
                widget_type="map",
                data_source="geographic_distribution",
                position={"x": 0, "y": 4, "width": 6, "height": 4}
            ),
            DashboardWidget(
                widget_id="category_pie",
                title="Popularnost Kategorija",
                widget_type="chart",
                data_source="category_popularity",
                config={"chart_type": "pie"},
                position={"x": 6, "y": 4, "width": 6, "height": 4}
            )
        ]
        
        self.widgets.extend(default_widgets)
    
    def add_analytics_data(self, metric_type: MetricType, value: float, 
                          metadata: Dict[str, Any] = None, 
                          dimensions: Dict[str, str] = None,
                          timestamp: datetime = None):
        """Dodaje podatke za analitiku"""
        
        if timestamp is None:
            timestamp = datetime.now()
        
        data_point = AnalyticsData(
            metric_type=metric_type,
            timestamp=timestamp,
            value=value,
            metadata=metadata or {},
            dimensions=dimensions or {}
        )
        
        self.analytics_data.append(data_point)
        logger.debug(f"Dodana analitika: {metric_type.value} = {value}")
    
    def generate_grants_overview_report(self, start_date: datetime = None, 
                                      end_date: datetime = None) -> Dict[str, Any]:
        """Generiše pregled grantova"""
        
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()
        
        # Filtriraj podatke
        grants_data = [
            d for d in self.analytics_data 
            if (d.metric_type == MetricType.GRANTS_COUNT and 
                start_date <= d.timestamp <= end_date)
        ]
        
        if not grants_data:
            return {"error": "Nema podataka za odabrani period"}
        
        # Osnovne statistike
        total_grants = sum(d.value for d in grants_data)
        avg_daily_grants = total_grants / max(1, (end_date - start_date).days)
        
        # Trend analiza
        df = pd.DataFrame([
            {
                'date': d.timestamp.date(),
                'count': d.value,
                'source': d.dimensions.get('source', 'unknown'),
                'category': d.dimensions.get('category', 'unknown')
            }
            for d in grants_data
        ])
        
        # Grupiranje po datumu
        daily_stats = df.groupby('date')['count'].sum().reset_index()
        
        # Trend (linearni)
        if len(daily_stats) > 1:
            x = np.arange(len(daily_stats))
            y = daily_stats['count'].values
            trend_slope = np.polyfit(x, y, 1)[0]
        else:
            trend_slope = 0
        
        # Top izvori
        source_stats = df.groupby('source')['count'].sum().sort_values(ascending=False)
        
        # Top kategorije
        category_stats = df.groupby('category')['count'].sum().sort_values(ascending=False)
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": (end_date - start_date).days
            },
            "summary": {
                "total_grants": int(total_grants),
                "avg_daily_grants": round(avg_daily_grants, 2),
                "trend_slope": round(trend_slope, 3),
                "trend_direction": "rastući" if trend_slope > 0 else "opadajući" if trend_slope < 0 else "stabilan"
            },
            "daily_breakdown": daily_stats.to_dict('records'),
            "top_sources": source_stats.head(10).to_dict(),
            "top_categories": category_stats.head(10).to_dict(),
            "generated_at": datetime.now().isoformat()
        }
    
    def generate_user_activity_report(self, start_date: datetime = None, 
                                    end_date: datetime = None) -> Dict[str, Any]:
        """Generiše izvještaj o aktivnosti korisnika"""
        
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()
        
        # Filtriraj podatke
        user_data = [
            d for d in self.analytics_data 
            if (d.metric_type == MetricType.USER_ACTIVITY and 
                start_date <= d.timestamp <= end_date)
        ]
        
        if not user_data:
            return {"error": "Nema podataka o korisnicima"}
        
        # Kreiraj DataFrame
        df = pd.DataFrame([
            {
                'date': d.timestamp.date(),
                'hour': d.timestamp.hour,
                'activity_type': d.dimensions.get('activity_type', 'unknown'),
                'user_id': d.dimensions.get('user_id', 'anonymous'),
                'value': d.value
            }
            for d in user_data
        ])
        
        # Dnevna aktivnost
        daily_activity = df.groupby('date')['value'].sum().reset_index()
        
        # Aktivnost po satima
        hourly_activity = df.groupby('hour')['value'].sum().reset_index()
        
        # Tipovi aktivnosti
        activity_types = df.groupby('activity_type')['value'].sum().sort_values(ascending=False)
        
        # Jedinstveni korisnici
        unique_users_daily = df.groupby('date')['user_id'].nunique().reset_index()
        unique_users_daily.columns = ['date', 'unique_users']
        
        # Peak sati
        peak_hour = hourly_activity.loc[hourly_activity['value'].idxmax(), 'hour']
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_activities": int(df['value'].sum()),
                "unique_users": df['user_id'].nunique(),
                "avg_daily_activities": round(daily_activity['value'].mean(), 2),
                "peak_hour": int(peak_hour),
                "most_popular_activity": activity_types.index[0] if len(activity_types) > 0 else "unknown"
            },
            "daily_activity": daily_activity.to_dict('records'),
            "hourly_activity": hourly_activity.to_dict('records'),
            "activity_types": activity_types.to_dict(),
            "unique_users_trend": unique_users_daily.to_dict('records'),
            "generated_at": datetime.now().isoformat()
        }
    
    def generate_revenue_report(self, start_date: datetime = None, 
                              end_date: datetime = None) -> Dict[str, Any]:
        """Generiše izvještaj o prihodima"""
        
        if start_date is None:
            start_date = datetime.now() - timedelta(days=90)
        if end_date is None:
            end_date = datetime.now()
        
        # Filtriraj podatke
        revenue_data = [
            d for d in self.analytics_data 
            if (d.metric_type == MetricType.SUBSCRIPTION_REVENUE and 
                start_date <= d.timestamp <= end_date)
        ]
        
        if not revenue_data:
            return {"error": "Nema podataka o prihodima"}
        
        # Kreiraj DataFrame
        df = pd.DataFrame([
            {
                'date': d.timestamp.date(),
                'month': d.timestamp.strftime('%Y-%m'),
                'revenue': d.value,
                'subscription_type': d.dimensions.get('subscription_type', 'unknown'),
                'currency': d.dimensions.get('currency', 'BAM')
            }
            for d in revenue_data
        ])
        
        # Mjesečni prihodi
        monthly_revenue = df.groupby('month')['revenue'].sum().reset_index()
        
        # Prihodi po tipovima pretplata
        subscription_revenue = df.groupby('subscription_type')['revenue'].sum().sort_values(ascending=False)
        
        # Rast prihoda (MoM)
        if len(monthly_revenue) > 1:
            current_month = monthly_revenue.iloc[-1]['revenue']
            previous_month = monthly_revenue.iloc[-2]['revenue']
            growth_rate = ((current_month - previous_month) / previous_month * 100) if previous_month > 0 else 0
        else:
            growth_rate = 0
        
        # Prosječni mjesečni prihod
        avg_monthly_revenue = monthly_revenue['revenue'].mean()
        
        # Projekcija (jednostavna linearna)
        if len(monthly_revenue) > 2:
            x = np.arange(len(monthly_revenue))
            y = monthly_revenue['revenue'].values
            trend_slope = np.polyfit(x, y, 1)[0]
            next_month_projection = y[-1] + trend_slope
        else:
            next_month_projection = avg_monthly_revenue
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_revenue": round(df['revenue'].sum(), 2),
                "avg_monthly_revenue": round(avg_monthly_revenue, 2),
                "current_month_growth": round(growth_rate, 2),
                "next_month_projection": round(next_month_projection, 2),
                "top_subscription_type": subscription_revenue.index[0] if len(subscription_revenue) > 0 else "unknown"
            },
            "monthly_revenue": monthly_revenue.to_dict('records'),
            "subscription_breakdown": subscription_revenue.to_dict(),
            "currency": "BAM",
            "generated_at": datetime.now().isoformat()
        }
    
    def generate_eligibility_analysis(self, start_date: datetime = None, 
                                    end_date: datetime = None) -> Dict[str, Any]:
        """Generiše analizu podobnosti"""
        
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()
        
        # Filtriraj podatke
        eligibility_data = [
            d for d in self.analytics_data 
            if (d.metric_type == MetricType.ELIGIBILITY_SCORES and 
                start_date <= d.timestamp <= end_date)
        ]
        
        if not eligibility_data:
            return {"error": "Nema podataka o podobnosti"}
        
        # Kreiraj DataFrame
        df = pd.DataFrame([
            {
                'date': d.timestamp.date(),
                'score': d.value,
                'grant_category': d.dimensions.get('grant_category', 'unknown'),
                'organization_type': d.dimensions.get('organization_type', 'unknown'),
                'user_id': d.dimensions.get('user_id', 'anonymous')
            }
            for d in eligibility_data
        ])
        
        # Osnovne statistike
        avg_score = df['score'].mean()
        median_score = df['score'].median()
        std_score = df['score'].std()
        
        # Distribucija score-ova
        score_ranges = {
            'visoka (80-100%)': len(df[df['score'] >= 80]),
            'srednja (60-79%)': len(df[(df['score'] >= 60) & (df['score'] < 80)]),
            'niska (40-59%)': len(df[(df['score'] >= 40) & (df['score'] < 60)]),
            'vrlo_niska (0-39%)': len(df[df['score'] < 40])
        }
        
        # Score po kategorijama
        category_scores = df.groupby('grant_category')['score'].agg(['mean', 'count']).reset_index()
        category_scores.columns = ['category', 'avg_score', 'count']
        category_scores = category_scores.sort_values('avg_score', ascending=False)
        
        # Score po tipovima organizacija
        org_scores = df.groupby('organization_type')['score'].agg(['mean', 'count']).reset_index()
        org_scores.columns = ['organization_type', 'avg_score', 'count']
        org_scores = org_scores.sort_values('avg_score', ascending=False)
        
        # Trend po danima
        daily_scores = df.groupby('date')['score'].mean().reset_index()
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_assessments": len(df),
                "avg_score": round(avg_score, 2),
                "median_score": round(median_score, 2),
                "std_deviation": round(std_score, 2),
                "success_rate": round(len(df[df['score'] >= 60]) / len(df) * 100, 2)
            },
            "score_distribution": score_ranges,
            "category_performance": category_scores.to_dict('records'),
            "organization_performance": org_scores.to_dict('records'),
            "daily_trend": daily_scores.to_dict('records'),
            "generated_at": datetime.now().isoformat()
        }
    
    def create_grants_overview_chart(self, data: Dict[str, Any]) -> go.Figure:
        """Kreira chart za pregled grantova"""
        
        if "daily_breakdown" not in data:
            return go.Figure().add_annotation(text="Nema podataka", showarrow=False)
        
        df = pd.DataFrame(data["daily_breakdown"])
        df['date'] = pd.to_datetime(df['date'])
        
        fig = go.Figure()
        
        # Dodaj liniju trenda
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['count'],
            mode='lines+markers',
            name='Broj grantova',
            line=dict(color='#2563eb', width=3),
            marker=dict(size=8)
        ))
        
        # Dodaj trend liniju
        if len(df) > 1:
            x_numeric = np.arange(len(df))
            trend_line = np.polyval(np.polyfit(x_numeric, df['count'], 1), x_numeric)
            
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=trend_line,
                mode='lines',
                name='Trend',
                line=dict(color='#ef4444', width=2, dash='dash'),
                opacity=0.7
            ))
        
        fig.update_layout(
            title="Broj Grantova po Danima",
            xaxis_title="Datum",
            yaxis_title="Broj Grantova",
            hovermode='x unified',
            template='plotly_white'
        )
        
        return fig
    
    def create_user_activity_chart(self, data: Dict[str, Any]) -> go.Figure:
        """Kreira chart za aktivnost korisnika"""
        
        if "hourly_activity" not in data:
            return go.Figure().add_annotation(text="Nema podataka", showarrow=False)
        
        hourly_df = pd.DataFrame(data["hourly_activity"])
        daily_df = pd.DataFrame(data["daily_activity"])
        daily_df['date'] = pd.to_datetime(daily_df['date'])
        
        # Kreiraj subplot
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Dnevna Aktivnost', 'Aktivnost po Satima'),
            vertical_spacing=0.1
        )
        
        # Dnevna aktivnost
        fig.add_trace(
            go.Scatter(
                x=daily_df['date'],
                y=daily_df['value'],
                mode='lines+markers',
                name='Dnevna aktivnost',
                line=dict(color='#10b981')
            ),
            row=1, col=1
        )
        
        # Aktivnost po satima
        fig.add_trace(
            go.Bar(
                x=hourly_df['hour'],
                y=hourly_df['value'],
                name='Aktivnost po satima',
                marker_color='#8b5cf6'
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            height=600,
            showlegend=False,
            template='plotly_white'
        )
        
        return fig
    
    def create_revenue_chart(self, data: Dict[str, Any]) -> go.Figure:
        """Kreira chart za prihode"""
        
        if "monthly_revenue" not in data:
            return go.Figure().add_annotation(text="Nema podataka", showarrow=False)
        
        df = pd.DataFrame(data["monthly_revenue"])
        
        fig = go.Figure()
        
        # Bar chart za mjesečne prihode
        fig.add_trace(go.Bar(
            x=df['month'],
            y=df['revenue'],
            name='Mjesečni prihodi',
            marker_color='#f59e0b',
            text=df['revenue'].round(2),
            textposition='auto'
        ))
        
        # Dodaj trend liniju
        if len(df) > 1:
            x_numeric = np.arange(len(df))
            trend_line = np.polyval(np.polyfit(x_numeric, df['revenue'], 1), x_numeric)
            
            fig.add_trace(go.Scatter(
                x=df['month'],
                y=trend_line,
                mode='lines',
                name='Trend',
                line=dict(color='#ef4444', width=3),
                yaxis='y2'
            ))
        
        fig.update_layout(
            title="Mjesečni Prihodi",
            xaxis_title="Mjesec",
            yaxis_title="Prihod (BAM)",
            yaxis2=dict(overlaying='y', side='right'),
            template='plotly_white'
        )
        
        return fig
    
    def create_geographic_distribution_chart(self, data: Dict[str, Any]) -> go.Figure:
        """Kreira geografsku distribuciju"""
        
        # Simulirani podaci za BiH
        bih_data = {
            'Sarajevo': 45,
            'Banja Luka': 32,
            'Tuzla': 28,
            'Zenica': 22,
            'Mostar': 18,
            'Bihać': 15,
            'Prijedor': 12,
            'Doboj': 10,
            'Trebinje': 8,
            'Cazin': 6
        }
        
        cities = list(bih_data.keys())
        values = list(bih_data.values())
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=cities,
            y=values,
            marker_color='#6366f1',
            text=values,
            textposition='auto'
        ))
        
        fig.update_layout(
            title="Distribucija Korisnika po Gradovima",
            xaxis_title="Grad",
            yaxis_title="Broj Korisnika",
            template='plotly_white'
        )
        
        return fig
    
    def create_category_popularity_chart(self, data: Dict[str, Any]) -> go.Figure:
        """Kreira chart popularnosti kategorija"""
        
        # Simulirani podaci
        categories = {
            'Inovacije': 35,
            'Digitalizacija': 28,
            'Zelena ekonomija': 22,
            'Turizam': 18,
            'Poljoprivreda': 15,
            'Obrazovanje': 12,
            'Zdravstvo': 10,
            'Kultura': 8,
            'Sport': 5,
            'Energetika': 7
        }
        
        fig = go.Figure()
        
        fig.add_trace(go.Pie(
            labels=list(categories.keys()),
            values=list(categories.values()),
            hole=0.4,
            marker_colors=px.colors.qualitative.Set3
        ))
        
        fig.update_layout(
            title="Popularnost Kategorija Grantova",
            template='plotly_white'
        )
        
        return fig
    
    def create_eligibility_distribution_chart(self, data: Dict[str, Any]) -> go.Figure:
        """Kreira chart distribucije podobnosti"""
        
        if "score_distribution" not in data:
            return go.Figure().add_annotation(text="Nema podataka", showarrow=False)
        
        distribution = data["score_distribution"]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=list(distribution.keys()),
            y=list(distribution.values()),
            marker_color=['#10b981', '#f59e0b', '#ef4444', '#6b7280'],
            text=list(distribution.values()),
            textposition='auto'
        ))
        
        fig.update_layout(
            title="Distribucija Score-ova Podobnosti",
            xaxis_title="Nivo Podobnosti",
            yaxis_title="Broj Procjena",
            template='plotly_white'
        )
        
        return fig
    
    def generate_comprehensive_dashboard(self, start_date: datetime = None, 
                                       end_date: datetime = None) -> Dict[str, Any]:
        """Generiše kompletni dashboard"""
        
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()
        
        # Generiši sve izvještaje
        grants_report = self.generate_grants_overview_report(start_date, end_date)
        user_report = self.generate_user_activity_report(start_date, end_date)
        revenue_report = self.generate_revenue_report(start_date, end_date)
        eligibility_report = self.generate_eligibility_analysis(start_date, end_date)
        
        # Kreiraj chart-ove
        charts = {}
        
        if "error" not in grants_report:
            charts["grants_chart"] = self.create_grants_overview_chart(grants_report).to_json()
        
        if "error" not in user_report:
            charts["user_activity_chart"] = self.create_user_activity_chart(user_report).to_json()
        
        if "error" not in revenue_report:
            charts["revenue_chart"] = self.create_revenue_chart(revenue_report).to_json()
        
        if "error" not in eligibility_report:
            charts["eligibility_chart"] = self.create_eligibility_distribution_chart(eligibility_report).to_json()
        
        charts["geographic_chart"] = self.create_geographic_distribution_chart({}).to_json()
        charts["category_chart"] = self.create_category_popularity_chart({}).to_json()
        
        # KPI metrike
        kpis = {
            "total_grants": grants_report.get("summary", {}).get("total_grants", 0),
            "total_users": user_report.get("summary", {}).get("unique_users", 0),
            "monthly_revenue": revenue_report.get("summary", {}).get("total_revenue", 0),
            "avg_eligibility_score": eligibility_report.get("summary", {}).get("avg_score", 0),
            "success_rate": eligibility_report.get("summary", {}).get("success_rate", 0),
            "user_growth": user_report.get("summary", {}).get("avg_daily_activities", 0)
        }
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "kpis": kpis,
            "reports": {
                "grants": grants_report,
                "users": user_report,
                "revenue": revenue_report,
                "eligibility": eligibility_report
            },
            "charts": charts,
            "widgets": [widget.__dict__ for widget in self.widgets],
            "generated_at": datetime.now().isoformat()
        }
    
    def export_dashboard_html(self, dashboard_data: Dict[str, Any], 
                            filename: str = None) -> str:
        """Izvozi dashboard kao HTML"""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"finassist_dashboard_{timestamp}.html"
        
        html_template = """
<!DOCTYPE html>
<html lang="bs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FinAssist BH - Analytics Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f8fafc;
        }
        .header {
            background: linear-gradient(135deg, #2563eb, #1d4ed8);
            color: white;
            padding: 0;
            border-radius: 12px;
            margin-bottom: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
        }
        .header p {
            margin: 0;
            opacity: 0.9;
        }
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .kpi-card {
            background: white;
            padding: 0;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
        }
        .kpi-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #2563eb;
            margin-bottom: 10px;
        }
        .kpi-label {
            color: #6b7280;
            font-size: 1.1em;
        }
        .chart-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 30px;
        }
        .chart-container {
            background: white;
            padding: 0;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .chart-title {
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 15px;
            color: #374151;
        }
        .footer {
            text-align: center;
            margin-top: 50px;
            color: #6b7280;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>FinAssist BH Analytics Dashboard</h1>
        <p>Period: {start_date} - {end_date}</p>
        <p>Generirano: {generated_at}</p>
    </div>
    
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-value">{total_grants}</div>
            <div class="kpi-label">Ukupno Grantova</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">{total_users}</div>
            <div class="kpi-label">Aktivni Korisnici</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">{monthly_revenue:.0f} BAM</div>
            <div class="kpi-label">Mjesečni Prihod</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">{avg_eligibility_score:.1f}%</div>
            <div class="kpi-label">Prosječna Podobnost</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">{success_rate:.1f}%</div>
            <div class="kpi-label">Stopa Uspjeha</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">{user_growth:.1f}</div>
            <div class="kpi-label">Dnevna Aktivnost</div>
        </div>
    </div>
    
    <div class="chart-grid">
        <div class="chart-container">
            <div class="chart-title">Pregled Grantova</div>
            <div id="grants-chart"></div>
        </div>
        <div class="chart-container">
            <div class="chart-title">Aktivnost Korisnika</div>
            <div id="user-activity-chart"></div>
        </div>
        <div class="chart-container">
            <div class="chart-title">Mjesečni Prihodi</div>
            <div id="revenue-chart"></div>
        </div>
        <div class="chart-container">
            <div class="chart-title">Distribucija Podobnosti</div>
            <div id="eligibility-chart"></div>
        </div>
        <div class="chart-container">
            <div class="chart-title">Geografska Distribucija</div>
            <div id="geographic-chart"></div>
        </div>
        <div class="chart-container">
            <div class="chart-title">Popularnost Kategorija</div>
            <div id="category-chart"></div>
        </div>
    </div>
    
    <div class="footer">
        <p>FinAssist BH - Vaš ključ do EU i nacionalnih grantova</p>
        <p>© 2026 FinAssist BH. Sva prava zadržana.</p>
    </div>
    
    <script>
        // Render charts
        {chart_scripts}
    </script>
</body>
</html>
        """
        
        # Pripremi chart script-ove
        chart_scripts = []
        
        for chart_id, chart_json in dashboard_data.get("charts", {}).items():
            element_id = chart_id.replace("_", "-")
            script = f"""
            var {chart_id}_data = {chart_json};
            Plotly.newPlot('{element_id}', {chart_id}_data.data, {chart_id}_data.layout, {{responsive: true}});
            """
            chart_scripts.append(script)
        
        # Format HTML
        kpis = dashboard_data.get("kpis", {})
        period = dashboard_data.get("period", {})
        
        html_content = html_template.format(
            start_date=period.get("start_date", ""),
            end_date=period.get("end_date", ""),
            generated_at=dashboard_data.get("generated_at", ""),
            total_grants=kpis.get("total_grants", 0),
            total_users=kpis.get("total_users", 0),
            monthly_revenue=kpis.get("monthly_revenue", 0),
            avg_eligibility_score=kpis.get("avg_eligibility_score", 0),
            success_rate=kpis.get("success_rate", 0),
            user_growth=kpis.get("user_growth", 0),
            chart_scripts="\n".join(chart_scripts)
        )
        
        # Spremi HTML
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"Dashboard izvezen u {filename}")
        return filename
    
    def get_analytics_summary(self) -> Dict[str, Any]:
        """Vraća sažetak analitike"""
        
        total_data_points = len(self.analytics_data)
        
        # Distribucija po tipovima metrika
        metric_distribution = {}
        for data_point in self.analytics_data:
            metric_type = data_point.metric_type.value
            metric_distribution[metric_type] = metric_distribution.get(metric_type, 0) + 1
        
        # Najnoviji podaci
        if self.analytics_data:
            latest_data = max(self.analytics_data, key=lambda x: x.timestamp)
            latest_timestamp = latest_data.timestamp
        else:
            latest_timestamp = None
        
        # Najstariji podaci
        if self.analytics_data:
            oldest_data = min(self.analytics_data, key=lambda x: x.timestamp)
            oldest_timestamp = oldest_data.timestamp
        else:
            oldest_timestamp = None
        
        return {
            "total_data_points": total_data_points,
            "metric_distribution": metric_distribution,
            "data_range": {
                "oldest": oldest_timestamp.isoformat() if oldest_timestamp else None,
                "latest": latest_timestamp.isoformat() if latest_timestamp else None
            },
            "active_widgets": len([w for w in self.widgets if w.is_active]),
            "total_widgets": len(self.widgets),
            "cache_size": len(self.cached_reports)
        }

# Primjer korištenja
def main():
    """Testiranje analytics dashboard-a"""
    
    # Konfiguracija
    config = {
        'cache_enabled': True,
        'export_path': './exports/'
    }
    
    # Kreiraj dashboard
    dashboard = FinAssistAnalyticsDashboard(config)
    
    # Dodaj test podatke
    import random
    from datetime import datetime, timedelta
    
    # Simuliraj podatke za zadnjih 30 dana
    for i in range(30):
        date = datetime.now() - timedelta(days=i)
        
        # Grantovi
        dashboard.add_analytics_data(
            MetricType.GRANTS_COUNT,
            random.randint(5, 25),
            dimensions={'source': random.choice(['EU', 'FBiH', 'RS', 'Kantoni'])},
            timestamp=date
        )
        
        # Korisnici
        dashboard.add_analytics_data(
            MetricType.USER_ACTIVITY,
            random.randint(50, 200),
            dimensions={'activity_type': random.choice(['login', 'search', 'assessment'])},
            timestamp=date
        )
        
        # Prihodi
        if random.random() > 0.7:  # 30% dana s prihodima
            dashboard.add_analytics_data(
                MetricType.SUBSCRIPTION_REVENUE,
                random.uniform(100, 1000),
                dimensions={'subscription_type': random.choice(['STANDARD', 'PREMIUM'])},
                timestamp=date
            )
        
        # Podobnost
        for _ in range(random.randint(3, 15)):
            dashboard.add_analytics_data(
                MetricType.ELIGIBILITY_SCORES,
                random.uniform(20, 95),
                dimensions={
                    'grant_category': random.choice(['inovacije', 'digitalizacija', 'turizam']),
                    'organization_type': random.choice(['MSP', 'NGO', 'startup'])
                },
                timestamp=date
            )
    
    # Generiraj dashboard
    dashboard_data = dashboard.generate_comprehensive_dashboard()
    
    print("Dashboard generiran!")
    print(f"KPIs: {dashboard_data['kpis']}")
    
    # Izvezi HTML
    html_file = dashboard.export_dashboard_html(dashboard_data)
    print(f"HTML dashboard: {html_file}")
    
    # Prikaži sažetak
    summary = dashboard.get_analytics_summary()
    print(f"Sažetak analitike: {summary}")

if __name__ == "__main__":
    main()
