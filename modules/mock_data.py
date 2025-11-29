# modules/mock_data.py

def get_mock_market_cards():
    """메인 대시보드 상단에 보여줄 임시 지표 카드 데이터."""
    return [
        {"label": "S&P500", "value": "5,000.12", "delta": "+0.52%"},
        {"label": "NASDAQ", "value": "16,123.45", "delta": "+0.83%"},
        {"label": "USD/KRW", "value": "1,350.20원", "delta": "-3.10"},
        {"label": "미국 10Y 국채", "value": "3.95%", "delta": "-0.06%"},
    ]