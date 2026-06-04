from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from phemex_strategy_observer import replay_can_accept_trade, update_replay_trades, Candle
from trade_value_gate import TradeValueGate


def _trade(status='open', symbol='BTCUSDT', side='long'):
    return {
        'id': f'{symbol}-{side}',
        'symbol': symbol,
        'side': side,
        'status': status,
        'created_at': 1,
        'expires_at': 100,
        'entry': 100.0,
        'stop_loss': 95.0,
        'take_profit': 110.0,
        'result_r': None,
        'planned_quantity_asset': 1.0,
        'fee_rate': 0.0,
    }


def check_replay_respects_active_limits() -> None:
    cfg = {'max_open_trades_total': 3, 'max_open_trades_per_asset': 1, 'block_same_direction_correlated_trades': True}
    ok, reason = replay_can_accept_trade([_trade('open')], _trade('pending'), cfg)
    if ok or reason != 'max_open_trades_per_asset':
        raise AssertionError(f'expected same asset block, got {ok=} {reason=}')


def check_replay_same_candle_exit_after_fill() -> None:
    trade = _trade('pending')
    candle = Candle(timestamp=2, interval=60, last_close=99.0, open=99.0, high=111.0, low=99.0, close=108.0, volume=1.0, turnover=1.0)
    events = update_replay_trades([trade], candle)
    statuses = [event.get('status') for event in events]
    if statuses != ['open', 'tp']:
        raise AssertionError(f'expected open then tp on same candle, got {statuses}')
    if trade.get('status') != 'tp':
        raise AssertionError(f'trade should be tp, got {trade.get("status")}')


def check_fee_to_risk_gate_blocks_expensive_trade() -> None:
    gate = TradeValueGate({
        'estimated_taker_fee_rate': 0.0006,
        'max_fee_to_risk_fraction': 0.25,
        'min_net_profit_fraction': 0.0,
    })
    result = gate.evaluate({
        'symbol': 'BTCUSDT',
        'decision': 'LONG',
        'entry_price': 77000.0,
        'sl_price': 76900.0,
        'tp_price': 77160.0,
        'planned_quantity_asset': 0.1,
    })
    if result.get('trade_allowed') is not False or result.get('reason') != 'fee_to_risk_too_high':
        raise AssertionError(f'expected fee/risk block, got {result}')
    if float(result.get('fee_to_risk_fraction') or 0.0) <= float(result.get('max_fee_to_risk_fraction') or 0.0):
        raise AssertionError(f'expected fee/risk above max, got {result}')


def main() -> None:
    check_replay_respects_active_limits()
    check_replay_same_candle_exit_after_fill()
    check_fee_to_risk_gate_blocks_expensive_trade()
    print('Replay strategy mechanics checks OK')


if __name__ == '__main__':
    main()
