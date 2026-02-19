# app/routes/common.py
"""공통 API 라우트"""

import os
import json
import traceback
import pandas as pd
import yfinance as yf
import sys
import subprocess
from flask import Blueprint, jsonify, request, Response, stream_with_context

# SECTOR_MAP와 get_sector가 정의된 utils 모듈이 없으므로 임시 정의하거나 
# 나중에 생성할 예정입니다. (PART_03.md에 import 문이 있으므로 유지하되 파일 생성 필요)
try:
    from app.utils.cache import get_sector, SECTOR_MAP
except ImportError:
    # 임시 정의 (파일이 없을 경우 대비)
    SECTOR_MAP = {}
    def get_sector(ticker):
        return "기타"

common_bp = Blueprint('common', __name__)

# 티커(Ticker) 매핑(Mapping) 정보 로드
try:
    map_df = pd.read_csv('ticker_to_yahoo_map.csv', dtype=str)
    TICKER_TO_YAHOO_MAP = dict(zip(map_df['ticker'], map_df['yahoo_ticker']))
    print(f"Loaded {len(TICKER_TO_YAHOO_MAP)} verified ticker mappings.")
except Exception as e:
    print(f"Error loading ticker map: {e}")
    TICKER_TO_YAHOO_MAP = {}


@common_bp.route('/portfolio')
def get_portfolio_data():
    """포트폴리오 데이터 - KR Market"""
    try:
        target_date = request.args.get('date')
        
        if target_date:
            # --- 과거 데이터 모드(Historical Data Mode) ---
            csv_path = os.path.join('us_market', 'data', 'recommendation_history.csv')
            if not os.path.exists(csv_path):
                return jsonify({'error': 'History not found'}), 404
                
            df = pd.read_csv(csv_path, dtype={'ticker': str})
            df = df[df['recommendation_date'] == target_date]
            top_holdings_df = df.sort_values(by='final_investment_score', ascending=False).head(10)
            top_picks = top_holdings_df
            
            # 실시간 가격 데이터 가져오기(Fetch)
            tickers = top_holdings_df['ticker'].tolist()
            current_prices = {}
            # (가격 조회 로직 생략 또는 구현 필요)
            
            # 데이터 변환
            holdings = []
            for _, row in top_holdings_df.iterrows():
                ticker = row['ticker']
                holdings.append({
                    'symbol': ticker,
                    'name': row.get('name', ticker),
                    'quantity': 100,  # 더미 데이터
                    'avgPrice': row.get('entry_price', 0),
                    'currentPrice': row.get('closing_price', 0),
                    'pnl': 0,
                    'pnlPercent': 0,
                    'allocation': 10.0,
                    'sector': get_sector(ticker)
                })
                
            return jsonify({
                'holdings': holdings,
                'summary': {
                    'totalValue': 100000,
                    'pnl': 5000,
                    'pnlPercent': 5.0,
                    'buyingPower': 50000
                }
            })
            
        else:
            # --- 기본 모드(Default Mode): jongga_v2_latest.json 기반 ---
            json_path = 'jongga_v2_latest.json'
            if not os.path.exists(json_path):
                return jsonify({'holdings': [], 'summary': {'totalValue': 0, 'pnl': 0, 'pnlPercent': 0, 'buyingPower': 0}})
            
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            signals = data.get('signals', [])
            holdings = []
            for s in signals[:10]:
                ticker = s.get('ticker')
                holdings.append({
                    'symbol': ticker,
                    'name': s.get('name', ticker),
                    'quantity': 0,
                    'avgPrice': s.get('entry_price', 0),
                    'currentPrice': s.get('current_price', s.get('close', 0)),
                    'pnl': 0,
                    'pnlPercent': s.get('change_pct', 0),
                    'allocation': 0,
                    'sector': s.get('sector', '기타')
                })
            
            return jsonify({
                'holdings': holdings,
                'summary': {
                    'totalValue': 0,
                    'pnl': 0,
                    'pnlPercent': 0,
                    'buyingPower': 0
                }
            })
            
    except Exception as e:
        print(f"Error in /portfolio: {e}")
        return jsonify({'error': str(e)}), 500


@common_bp.route('/stock/<ticker>')
def get_stock_detail(ticker):
    """주식 상세 정보"""
    try:
        # 야후 티커 변환
        yahoo_ticker = TICKER_TO_YAHOO_MAP.get(ticker, f"{ticker}.KS")
        stock = yf.Ticker(yahoo_ticker)
        
        # 기본 정보
        info = stock.info
        
        # 히스토리 데이터 (최근 1개월)
        hist = stock.history(period="1mo")
        chart_data = []
        for d, row in hist.iterrows():
            chart_data.append({
                'date': d.strftime('%Y-%m-%d'),
                'close': row['Close'],
                'volume': row['Volume']
            })
            
        return jsonify({
            'info': {
                'name': info.get('longName', ticker),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'marketCap': info.get('marketCap', 0),
                'pe': info.get('trailingPE', 0),
                'dividendYield': info.get('dividendYield', 0)
            },
            'chart': chart_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@common_bp.route('/realtime-prices', methods=['POST'])
def get_realtime_prices():
    """실시간 가격 데이터 조회 (yfinance 기반)"""
    try:
        data = request.json
        tickers = data.get('tickers', [])
        
        if not tickers:
            return jsonify({})
            
        results = {}
        for t in tickers:
            yt = TICKER_TO_YAHOO_MAP.get(t, f"{t}.KS")
            try:
                # 빠른 조회를 위해 Ticker.fast_info 또는 history(period='1d') 사용
                s = yf.Ticker(yt)
                price = s.history(period='1d')['Close'].iloc[-1]
                results[t] = float(price)
            except:
                continue
                
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@common_bp.route('/run-analysis', methods=['POST'])
def run_analysis():
    """분석 스크립트 실행 (run.py --screen)"""
    try:
        # 비동기 실행 (결과는 파일로 확인)
        python_exe = sys.executable
        process = subprocess.Popen(
            [python_exe, 'run.py', '--screen'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return jsonify({'status': 'Started', 'pid': process.pid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@common_bp.route('/data-status')
def get_data_status():
    """데이터 수집 상태 확인"""
    files = {
        'signals': 'jongga_v2_latest.json',
        'history': 'recommendation_history.csv',
        'market_status': 'market_status.json'
    }
    
    status = {}
    for key, filename in files.items():
        if os.path.exists(filename):
            mtime = os.path.getmtime(filename)
            status[key] = {
                'exists': True,
                'last_updated': pd.to_datetime(mtime, unit='s').strftime('%Y-%m-%d %H:%M:%S'),
                'size': os.path.getsize(filename)
            }
        else:
            status[key] = {'exists': False}
            
    return jsonify(status)


@common_bp.route('/stream-update')
def stream_update():
    """서버 이벤트 스트리밍 (SSE)"""
    def generate():
        while True:
            # 실제로는 큐나 이벤트를 기다림
            import time
            time.sleep(10)
            yield f"data: {json.dumps({'type': 'ping', 'time': time.time()})}\n\n"
            
    return Response(stream_with_context(generate()), mimetype='text/event-stream')


@common_bp.route('/backtest-summary')
def get_backtest_summary():
    """전체 백테스트 요약 통계"""
    summary = {
        'vcp': {'status': 'No Data', 'win_rate': 0, 'total_trades': 0},
        'closing_bet': {'status': 'No Data', 'win_rate': 0, 'total_trades': 0}
    }
    
    debug_info = {}
    
    try:
        # 종가베팅(Closing Bet) 통계 계산
        json_path = 'jongga_v2_latest.json'
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 히스토리 데이터 로드 (없으면 현재 데이터로 대체)
            all_signals = data.get('signals', [])
            
            # recommendation_history.csv 가 있으면 거기서 통계 추출
            if os.path.exists('recommendation_history.csv'):
                try:
                    hist_df = pd.read_csv('recommendation_history.csv')
                    all_signals = hist_df.to_dict('records')
                except:
                    pass
            
            debug_info['total_signals'] = len(all_signals)
            
            if all_signals:
                wins = 0
                total_return = 0
                valid_count = 0
                
                for signal in all_signals:
                    entry_price = signal.get('entry_price', 0)
                    if entry_price <= 0:
                        continue
                    
                    change_pct = signal.get('change_pct', 0)
                    
                    if change_pct > 0:
                        est_return = 5.0
                        wins += 1
                    else:
                        est_return = -3.0
                    
                    total_return += est_return
                    valid_count += 1
                
                if valid_count > 0:
                    win_rate = (wins / valid_count) * 100
                    avg_return = total_return / valid_count
                    
                    summary['closing_bet'] = {
                        'status': 'OK',
                        'count': valid_count,
                        'win_rate': round(win_rate, 1),
                        'avg_return': round(avg_return, 2)
                    }
                else:
                    summary['closing_bet'] = {
                        'status': 'No Valid Signals',
                        'count': 0,
                        'win_rate': 0,
                        'avg_return': 0
                    }
            else:
                summary['closing_bet'] = {
                    'status': 'Accumulating',
                    'message': '과거 시그널 없음',
                    'count': 0,
                    'win_rate': 0,
                    'avg_return': 0
                }
                
    except Exception as e:
        debug_info['jongga_error'] = str(e)
        summary['closing_bet']['error'] = str(e)

    response = summary.copy()
    response['debug'] = debug_info
    return jsonify(response)
