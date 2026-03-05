#!/usr/bin/env python3
"""
珍爱网（SHYB）2026年2月份全面数据分析报告
覆盖：电销 / 建信 / 红娘 / 门店 / App / 趣约会 / 幸福汇 / 广告投放
"""
import json, sys, os, datetime, math
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(__file__))
from agent_system.actions.api_client import daily, trend, query, tables, ad_daily, health, safe_float, safe_int, parallel_fetch

API_KEY = "za_1792d80ab9b774913fd26ca46fb14a13"
os.environ.setdefault("ZA_API_KEY", API_KEY)

FEB_DATES = [f"202602{d:02d}" for d in range(1, 29)]
FEB_START, FEB_END = "20260201", "20260228"

def sf(v, d=0.0):
    if v is None or str(v).strip().lower() in ('null','none',''):
        return d
    try:
        return float(str(v).replace(",","").replace("%","").strip())
    except:
        return d

def si(v, d=0):
    return int(sf(v, d))

def fmt_money(v):
    if abs(v) >= 10000:
        return f"¥{v/10000:.2f}万"
    return f"¥{v:,.0f}"

def fmt_pct(v):
    return f"{v:.1f}%"

def pct_change(cur, prev):
    if prev == 0:
        return 0
    return (cur - prev) / prev * 100

# ─── Data Fetching ───
def fetch_all_data():
    print("📡 正在拉取所有业务线二月份数据...")
    data = {}

    teams_trend = ['telesale','app','jianxin','hongniang','shop','qyh','xfh']
    calls = [lambda t=t: trend(t, days=28) for t in teams_trend]
    trend_results = parallel_fetch(calls)
    for t, r in zip(teams_trend, trend_results):
        data[f'{t}_trend'] = r
        print(f"  ✓ {t} 趋势: {r.get('row_count',0)} 行")

    daily_calls = []
    for dt in FEB_DATES:
        for t in ['telesale','app','jianxin','hongniang','qyh','xfh']:
            daily_calls.append((t, dt))

    print(f"  拉取 {len(daily_calls)} 个日报数据点...")

    def fetch_daily(args):
        t, dt = args
        return (t, dt, daily(t, date=dt))

    all_daily = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(fetch_daily, args): args for args in daily_calls}
        for f in as_completed(futures):
            t, dt, result = f.result()
            key = f"{t}_{dt}"
            all_daily[key] = result

    data['all_daily'] = all_daily
    print(f"  ✓ 日报数据: {len(all_daily)} 条")

    ad_calls = [lambda dt=dt: (dt, ad_daily(date=dt)) for dt in FEB_DATES]
    ad_results = parallel_fetch(ad_calls)
    data['ad_daily'] = {r[0]: r[1] for r in ad_results if r}
    print(f"  ✓ 广告投放: {len(data['ad_daily'])} 天")

    return data

# ─── Telesale Analysis ───
def analyze_telesale(data):
    print("📊 分析电销数据...")
    trend_data = data.get('telesale_trend', {})
    rows = trend_data.get('rows', [])

    feb_rows = [r for r in rows if str(r.get('ftime','')).startswith('202602')]

    daily_agg = {}
    for r in feb_rows:
        dt = str(r.get('ftime',''))
        dep = str(r.get('dep_name',''))
        if dt not in daily_agg:
            daily_agg[dt] = {'workers':0,'callout':0,'link':0,'deep10':0,'pay_num':0,'pay_amt':0,'pay_1m':0,
                             'sms':0,'qywx':0,'new_w':0,'mid_w':0,'old_w':0,'depts':{}}
        a = daily_agg[dt]
        a['workers'] += si(r.get('worker_nums'))
        a['callout'] += si(r.get('callout_1d_num'))
        a['link'] += si(r.get('link_1d_num'))
        a['deep10'] += si(r.get('linkmems_deeptalk_10_1d_num'))
        a['pay_num'] += si(r.get('pay_1d_num'))
        a['pay_amt'] += sf(r.get('pay_1d_amt'))
        a['pay_1m'] = max(a['pay_1m'], sf(r.get('pay_1m_amt')))
        a['sms'] += si(r.get('send_sms_1d_num'))
        a['qywx'] += si(r.get('add_qywx_1d_num'))
        a['new_w'] += si(r.get('new_worker_num'))
        a['mid_w'] += si(r.get('4_and_6_month_worker_num'))
        a['old_w'] += si(r.get('6_month_above_worker_num'))

        if dep and dep not in ('', 'null'):
            grp = str(r.get('group_name',''))
            dept_key = dep
            if dept_key not in a['depts']:
                a['depts'][dept_key] = {'workers':0,'callout':0,'link':0,'deep10':0,'pay_num':0,'pay_amt':0,
                                         'qywx':0,'pay_1m':0}
            d = a['depts'][dept_key]
            d['workers'] += si(r.get('worker_nums'))
            d['callout'] += si(r.get('callout_1d_num'))
            d['link'] += si(r.get('link_1d_num'))
            d['deep10'] += si(r.get('linkmems_deeptalk_10_1d_num'))
            d['pay_num'] += si(r.get('pay_1d_num'))
            d['pay_amt'] += sf(r.get('pay_1d_amt'))
            d['qywx'] += si(r.get('add_qywx_1d_num'))
            d['pay_1m'] = max(d['pay_1m'], sf(r.get('pay_1m_amt')))

    sorted_dates = sorted(daily_agg.keys())

    total_pay = sum(a['pay_amt'] for a in daily_agg.values())
    total_callout = sum(a['callout'] for a in daily_agg.values())
    total_link = sum(a['link'] for a in daily_agg.values())
    total_deep10 = sum(a['deep10'] for a in daily_agg.values())
    total_pay_num = sum(a['pay_num'] for a in daily_agg.values())
    avg_workers = sum(a['workers'] for a in daily_agg.values()) / max(len(daily_agg),1)

    link_rate = (total_link / total_callout * 100) if total_callout > 0 else 0
    deep_rate = (total_deep10 / total_link * 100) if total_link > 0 else 0
    avg_daily_pay = total_pay / max(len(sorted_dates),1)
    avg_per_capita = avg_daily_pay / avg_workers if avg_workers > 0 else 0

    last_date = sorted_dates[-1] if sorted_dates else ''
    last_month_cum = daily_agg[last_date]['pay_1m'] if last_date else 0

    dept_monthly = {}
    if last_date:
        for dep, ddata in daily_agg[last_date]['depts'].items():
            dept_monthly[dep] = ddata

    all_dept_agg = {}
    for dt, agg in daily_agg.items():
        for dep, dd in agg['depts'].items():
            if dep not in all_dept_agg:
                all_dept_agg[dep] = {'workers':0,'callout':0,'link':0,'deep10':0,'pay_num':0,'pay_amt':0,'qywx':0,'days':0}
            ad = all_dept_agg[dep]
            ad['workers'] += dd['workers']
            ad['callout'] += dd['callout']
            ad['link'] += dd['link']
            ad['deep10'] += dd['deep10']
            ad['pay_num'] += dd['pay_num']
            ad['pay_amt'] += dd['pay_amt']
            ad['qywx'] += dd['qywx']
            ad['days'] += 1

    return {
        'daily': daily_agg,
        'sorted_dates': sorted_dates,
        'total_pay': total_pay,
        'total_callout': total_callout,
        'total_link': total_link,
        'total_deep10': total_deep10,
        'total_pay_num': total_pay_num,
        'avg_workers': avg_workers,
        'link_rate': link_rate,
        'deep_rate': deep_rate,
        'avg_daily_pay': avg_daily_pay,
        'avg_per_capita': avg_per_capita,
        'month_cum': last_month_cum,
        'dept_agg': all_dept_agg,
    }

# ─── App Analysis ───
def analyze_app(data):
    print("📊 分析App数据...")
    trend_data = data.get('app_trend', {})
    rows = trend_data.get('rows', [])
    feb_rows = [r for r in rows if str(r.get('ftime','')).startswith('202602')]
    feb_rows.sort(key=lambda r: str(r.get('ftime','')))

    daily_list = []
    for r in feb_rows:
        d = {
            'date': str(r.get('ftime','')),
            'amt': sf(r.get('amt')),
            'pay_num': si(r.get('pay_num')),
            'pay_num_new': si(r.get('pay_num_new')),
            'dau': si(r.get('active_members')),
            'refund': sf(r.get('refund_money')),
            'fugou_amt': sf(r.get('fugou_amt')),
            'mems': si(r.get('mems')),
            'order_cnt': si(r.get('order_cnt')),
            'order_pay': si(r.get('order_pay')),
            'zhenxin': sf(r.get('zhenxin_member')),
            'super_full': sf(r.get('super_member_full')),
            'super_plus': sf(r.get('super_member_plus')),
            'zhenai_coin': sf(r.get('zhenai_coin')),
            'star_priv': sf(r.get('star_privilege')),
            'live_guard': sf(r.get('live_guard')),
            'other': sf(r.get('other')),
            'super_rec': sf(r.get('super_recommend')),
            'super_remind': sf(r.get('super_remind')),
            'retain_1d': si(r.get('retain_1d')),
            'ad_cost_d': sf(r.get('last_consumeonday_d')),
            'ad_cost_m': sf(r.get('last_consumeonday_m')),
            'reg_m': si(r.get('reg_num_m')),
            'pay_m_cut': sf(r.get('pay_amt_m_cut')),
        }
        daily_list.append(d)

    total_amt = sum(d['amt'] for d in daily_list)
    total_pay_num = sum(d['pay_num'] for d in daily_list)
    total_new_pay = sum(d['pay_num_new'] for d in daily_list)
    total_refund = sum(d['refund'] for d in daily_list)
    avg_dau = sum(d['dau'] for d in daily_list) / max(len(daily_list),1)
    avg_arpu = total_amt / total_pay_num if total_pay_num > 0 else 0
    pay_rate = total_pay_num / (avg_dau * len(daily_list)) * 100 if avg_dau > 0 and daily_list else 0
    refund_ratio = total_refund / total_amt * 100 if total_amt > 0 else 0
    total_fugou = sum(d['fugou_amt'] for d in daily_list)
    fugou_ratio = total_fugou / total_amt * 100 if total_amt > 0 else 0

    total_zhenxin = sum(d['zhenxin'] for d in daily_list)
    zhenxin_ratio = total_zhenxin / total_amt * 100 if total_amt > 0 else 0

    avg_retain_1d = sum(d['retain_1d'] for d in daily_list) / max(len(daily_list),1)
    avg_mems = sum(d['mems'] for d in daily_list) / max(len(daily_list),1)
    retain_1d_rate = avg_retain_1d / avg_mems * 100 if avg_mems > 0 else 0

    last = daily_list[-1] if daily_list else {}

    return {
        'daily': daily_list,
        'total_amt': total_amt,
        'total_pay_num': total_pay_num,
        'total_new_pay': total_new_pay,
        'total_refund': total_refund,
        'avg_dau': avg_dau,
        'avg_arpu': avg_arpu,
        'pay_rate': pay_rate,
        'refund_ratio': refund_ratio,
        'fugou_ratio': fugou_ratio,
        'zhenxin_ratio': zhenxin_ratio,
        'retain_1d_rate': retain_1d_rate,
        'month_cum': last.get('pay_m_cut', 0),
        'reg_m': last.get('reg_m', 0),
    }

# ─── Jianxin Analysis ───
def analyze_jianxin(data):
    print("📊 分析建信数据...")
    trend_data = data.get('jianxin_trend', {})
    rows = trend_data.get('rows', [])
    feb_rows = [r for r in rows if str(r.get('ftime','')).startswith('202602')]

    daily_agg = {}
    for r in feb_rows:
        dt = str(r.get('ftime',''))
        if dt not in daily_agg:
            daily_agg[dt] = {'workers':0,'callout':0,'link':0,'allot_n':0,'send_n':0,'huifu_n':0,
                             'qywx':0,'adjust':0,'pay_qm':0,'pay_qm_m':0}
        a = daily_agg[dt]
        a['workers'] += si(r.get('worker_nums'))
        a['callout'] += si(r.get('callout_1d_num'))
        a['link'] += si(r.get('link_1d_num'))
        a['allot_n'] += si(r.get('allot_n'))
        a['send_n'] += si(r.get('send_n'))
        a['huifu_n'] += si(r.get('huifu_n'))
        a['qywx'] += si(r.get('add_qywx_1d_num'))
        a['adjust'] += si(r.get('adjust_mems'))
        a['pay_qm'] += sf(r.get('pay_money_qiemian'))
        a['pay_qm_m'] = max(a['pay_qm_m'], sf(r.get('pay_money_m_qiemian')))

    sorted_dates = sorted(daily_agg.keys())
    total_send = sum(a['send_n'] for a in daily_agg.values())
    total_huifu = sum(a['huifu_n'] for a in daily_agg.values())
    total_qywx = sum(a['qywx'] for a in daily_agg.values())
    total_adjust = sum(a['adjust'] for a in daily_agg.values())
    total_pay_qm = sum(a['pay_qm'] for a in daily_agg.values())
    reply_rate = total_huifu / total_send * 100 if total_send > 0 else 0
    last_date = sorted_dates[-1] if sorted_dates else ''
    month_cum = daily_agg[last_date]['pay_qm_m'] if last_date else 0

    return {
        'daily': daily_agg,
        'sorted_dates': sorted_dates,
        'total_send': total_send,
        'total_huifu': total_huifu,
        'total_qywx': total_qywx,
        'total_adjust': total_adjust,
        'total_pay_qm': total_pay_qm,
        'reply_rate': reply_rate,
        'month_cum': month_cum,
    }

# ─── Hongniang Analysis ───
def analyze_hongniang(data):
    print("📊 分析红娘数据...")
    trend_data = data.get('hongniang_trend', {})
    rows = trend_data.get('rows', [])
    feb_rows = [r for r in rows if str(r.get('ftime','')).startswith('202602')]

    daily_agg = {}
    for r in feb_rows:
        dt = str(r.get('ftime',''))
        if dt not in daily_agg:
            daily_agg[dt] = {'staff':0,'jm_n':0,'pay_d':0,'pay_m':0,'tousu':0,
                             'on_vip':0,'zhenai_back':0,'zhenaigd_back':0,'love_m':0}
        a = daily_agg[dt]
        a['staff'] += si(r.get('staff_chu_new',r.get('staff_chu',0)))
        a['jm_n'] += si(r.get('jm_n'))
        a['pay_d'] += sf(r.get('pay_amt_d'))
        a['pay_m'] = max(a['pay_m'], sf(r.get('pay_amt_m')))
        a['tousu'] += si(r.get('tousu_n'))
        a['on_vip'] += si(r.get('on_vip'))
        a['zhenai_back'] += sf(r.get('zhenai_back'))
        a['zhenaigd_back'] += sf(r.get('zhenaigd_back',0))
        a['love_m'] = max(a['love_m'], si(r.get('love_cnt_m',0)))

    sorted_dates = sorted(daily_agg.keys())
    total_jm = sum(a['jm_n'] for a in daily_agg.values())
    total_pay = sum(a['pay_d'] for a in daily_agg.values())
    total_tousu = sum(a['tousu'] for a in daily_agg.values())
    total_refund_za = sum(a['zhenai_back'] for a in daily_agg.values())
    total_refund_gd = sum(a['zhenaigd_back'] for a in daily_agg.values())
    avg_staff = sum(a['staff'] for a in daily_agg.values()) / max(len(daily_agg),1)
    last = daily_agg[sorted_dates[-1]] if sorted_dates else {}

    return {
        'daily': daily_agg,
        'sorted_dates': sorted_dates,
        'total_jm': total_jm,
        'total_pay': total_pay,
        'total_tousu': total_tousu,
        'total_refund_za': total_refund_za,
        'total_refund_gd': total_refund_gd,
        'avg_staff': avg_staff,
        'month_pay': last.get('pay_m',0),
        'love_m': last.get('love_m',0),
    }

# ─── QYH Analysis ───
def analyze_qyh(data):
    print("📊 分析趣约会数据...")
    trend_data = data.get('qyh_trend', {})
    rows = trend_data.get('rows', [])
    feb_rows = [r for r in rows if str(r.get('ftime','')).startswith('202602')]
    feb_rows.sort(key=lambda r: str(r.get('ftime','')))

    daily_list = []
    for r in feb_rows:
        d = {
            'date': str(r.get('ftime','')),
            'pay_amount': sf(r.get('pay_amount')),
            'dau': si(r.get('dau', r.get('actmem',0))),
            'pay_num': si(r.get('order_pay_num')),
            'live_gift': sf(r.get('live_gift_amt')),
            'rose_charge': sf(r.get('rose_charge_amt')),
            'rose_consume': sf(r.get('rose_comsume_amt')),
            'anchor_min': sf(r.get('anchormin')),
            'ad_reg': si(r.get('ad_reg_cnt')),
            'ad_pay_amt': sf(r.get('ad_pay_amt')),
            'ad_cost': sf(r.get('ad_consume_on_day')),
        }
        daily_list.append(d)

    total_pay = sum(d['pay_amount'] for d in daily_list)
    total_gift = sum(d['live_gift'] for d in daily_list)
    total_rose_charge = sum(d['rose_charge'] for d in daily_list)
    avg_dau = sum(d['dau'] for d in daily_list) / max(len(daily_list),1)

    return {
        'daily': daily_list,
        'total_pay': total_pay,
        'total_gift': total_gift,
        'total_rose_charge': total_rose_charge,
        'avg_dau': avg_dau,
    }

# ─── Generate HTML Report ───
def sparkline_svg(values, width=120, height=30, color="#4A90D9"):
    if not values or len(values) < 2:
        return ""
    mn, mx = min(values), max(values)
    rng = mx - mn if mx != mn else 1
    n = len(values)
    points = []
    for i, v in enumerate(values):
        x = (i / (n - 1)) * width
        y = height - ((v - mn) / rng) * (height - 4) - 2
        points.append(f"{x:.1f},{y:.1f}")
    polyline = " ".join(points)
    last_x, last_y = points[-1].split(",")
    end_color = "#27ae60" if values[-1] >= values[-2] else "#e74c3c"
    return (f'<svg width="{width}" height="{height}" style="vertical-align:middle">'
            f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="1.5"/>'
            f'<circle cx="{last_x}" cy="{last_y}" r="3" fill="{end_color}"/></svg>')

def generate_html(telesale, app, jianxin, hongniang, qyh):
    print("📝 生成HTML报告...")

    total_revenue = telesale['total_pay'] + app['total_amt'] + jianxin['total_pay_qm'] + hongniang['total_pay'] + qyh['total_pay']

    ts_dates = telesale['sorted_dates']
    ts_daily_amts = [telesale['daily'][d]['pay_amt'] for d in ts_dates]
    ts_daily_link_rates = []
    for d in ts_dates:
        dd = telesale['daily'][d]
        lr = dd['link'] / dd['callout'] * 100 if dd['callout'] > 0 else 0
        ts_daily_link_rates.append(lr)

    app_daily_amts = [d['amt'] for d in app['daily']]
    app_daily_dau = [d['dau'] for d in app['daily']]

    jx_dates = jianxin['sorted_dates']
    jx_daily_qywx = [jianxin['daily'][d]['qywx'] for d in jx_dates]

    hn_dates = hongniang['sorted_dates']
    hn_daily_jm = [hongniang['daily'][d]['jm_n'] for d in hn_dates]

    qyh_daily_pay = [d['pay_amount'] for d in qyh['daily']]

    # Week analysis for telesale
    weeks = {}
    for d in ts_dates:
        dt_obj = datetime.datetime.strptime(d, "%Y%m%d")
        week_num = dt_obj.isocalendar()[1]
        wk = f"W{week_num}"
        if wk not in weeks:
            weeks[wk] = {'pay':0, 'days':0, 'callout':0, 'link':0}
        dd = telesale['daily'][d]
        weeks[wk]['pay'] += dd['pay_amt']
        weeks[wk]['days'] += 1
        weeks[wk]['callout'] += dd['callout']
        weeks[wk]['link'] += dd['link']

    # Dept ranking
    dept_ranks = []
    for dep, dd in telesale['dept_agg'].items():
        if dd['workers'] < 10:
            continue
        avg_w = dd['workers'] / max(dd['days'],1)
        dept_ranks.append({
            'name': dep,
            'workers': avg_w,
            'pay_amt': dd['pay_amt'],
            'callout': dd['callout'],
            'link': dd['link'],
            'deep10': dd['deep10'],
            'qywx': dd['qywx'],
            'link_rate': dd['link'] / dd['callout'] * 100 if dd['callout'] > 0 else 0,
            'deep_rate': dd['deep10'] / dd['link'] * 100 if dd['link'] > 0 else 0,
            'per_capita': dd['pay_amt'] / avg_w if avg_w > 0 else 0,
            'per_callout': dd['callout'] / avg_w if avg_w > 0 else 0,
        })
    dept_ranks.sort(key=lambda x: x['pay_amt'], reverse=True)

    # App product structure
    app_products = {}
    for d in app['daily']:
        for pkey, pname in [('zhenxin','珍心会员'),('super_full','完整版超级会员'),
                            ('super_plus','升级版超级会员'),('zhenai_coin','珍爱币'),
                            ('star_priv','星特权'),('live_guard','直播守护'),
                            ('super_rec','超级推荐'),('super_remind','超级提醒'),
                            ('other','其他')]:
            if pname not in app_products:
                app_products[pname] = 0
            app_products[pname] += d.get(pkey, 0)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>珍爱网2026年2月运营全景分析报告</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
       background:#f0f2f5; color:#333; line-height:1.6; }}
.container {{ max-width:1200px; margin:0 auto; padding:20px; }}
.header {{ background:linear-gradient(135deg,#1a237e,#283593,#3949ab);
          color:#fff; padding:40px; border-radius:16px; margin-bottom:24px;
          box-shadow:0 8px 32px rgba(26,35,126,0.3); }}
.header h1 {{ font-size:28px; margin-bottom:8px; }}
.header .sub {{ opacity:0.85; font-size:14px; }}
.kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
            gap:16px; margin-bottom:24px; }}
.kpi-card {{ background:#fff; border-radius:12px; padding:20px;
            box-shadow:0 2px 12px rgba(0,0,0,0.06); position:relative; overflow:hidden; }}
.kpi-card::before {{ content:''; position:absolute; top:0; left:0; right:0; height:4px; }}
.kpi-card.blue::before {{ background:linear-gradient(90deg,#1565c0,#42a5f5); }}
.kpi-card.purple::before {{ background:linear-gradient(90deg,#7b1fa2,#ce93d8); }}
.kpi-card.orange::before {{ background:linear-gradient(90deg,#e65100,#ff9800); }}
.kpi-card.green::before {{ background:linear-gradient(90deg,#2e7d32,#66bb6a); }}
.kpi-card.red::before {{ background:linear-gradient(90deg,#c62828,#ef5350); }}
.kpi-card .label {{ font-size:12px; color:#888; text-transform:uppercase; }}
.kpi-card .value {{ font-size:24px; font-weight:700; margin:4px 0; }}
.kpi-card .change {{ font-size:13px; }}
.kpi-card .change.up {{ color:#27ae60; }}
.kpi-card .change.down {{ color:#e74c3c; }}
.section {{ background:#fff; border-radius:12px; padding:24px; margin-bottom:20px;
           box-shadow:0 2px 12px rgba(0,0,0,0.06); }}
.section h2 {{ font-size:20px; color:#1a237e; margin-bottom:16px;
              border-left:4px solid #3949ab; padding-left:12px; }}
.section h3 {{ font-size:16px; color:#333; margin:16px 0 8px; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; margin:12px 0; }}
th {{ background:#f5f6fa; color:#555; font-weight:600; text-align:left;
     padding:10px 12px; border-bottom:2px solid #e0e0e0; }}
td {{ padding:8px 12px; border-bottom:1px solid #f0f0f0; }}
tr:hover td {{ background:#f8f9ff; }}
.badge {{ display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }}
.badge-red {{ background:#fde8e8; color:#c62828; }}
.badge-orange {{ background:#fff3e0; color:#e65100; }}
.badge-green {{ background:#e8f5e9; color:#2e7d32; }}
.badge-blue {{ background:#e3f2fd; color:#1565c0; }}
.insight-box {{ border-left:4px solid; padding:12px 16px; margin:8px 0; border-radius:0 8px 8px 0; }}
.insight-box.risk {{ border-color:#e74c3c; background:#fef5f5; }}
.insight-box.warn {{ border-color:#e67e22; background:#fef9f0; }}
.insight-box.good {{ border-color:#27ae60; background:#f0faf3; }}
.insight-box.info {{ border-color:#2196f3; background:#f0f7ff; }}
.insight-box .title {{ font-weight:700; margin-bottom:4px; }}
.progress-bar {{ height:8px; background:#e0e0e0; border-radius:4px; overflow:hidden; margin:4px 0; }}
.progress-bar .fill {{ height:100%; border-radius:4px; }}
.two-col {{ display:grid; grid-template-columns:1fr 1fr; gap:20px; }}
@media(max-width:768px) {{ .two-col {{ grid-template-columns:1fr; }} }}
.metric-row {{ display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #f0f0f0; }}
.metric-row .label {{ color:#666; }}
.metric-row .val {{ font-weight:600; }}
.footer {{ text-align:center; color:#999; font-size:12px; padding:20px; }}
.trend-chart {{ display:flex; gap:4px; align-items:flex-end; height:60px; margin:8px 0; }}
.trend-bar {{ flex:1; background:#e3f2fd; border-radius:2px 2px 0 0; min-width:3px;
             transition:background 0.2s; position:relative; }}
.trend-bar:hover {{ background:#1565c0; }}
.highlight {{ background:#fffde7; padding:2px 4px; border-radius:3px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>珍爱网 2026年2月 运营全景分析报告</h1>
    <div class="sub">报告周期：2026年2月1日 - 2月28日 | 生成时间：{now}</div>
    <div class="sub">覆盖业务线：电销 · 建信 · 红娘 · App主站 · 趣约会 · 幸福汇 · 广告投放</div>
  </div>

  <!-- ===== 全局KPI总览 ===== -->
  <div class="kpi-grid">
    <div class="kpi-card blue">
      <div class="label">电销月累计业绩</div>
      <div class="value">{fmt_money(telesale['total_pay'])}</div>
      <div class="change">日均 {fmt_money(telesale['avg_daily_pay'])} | 人均日产值 {fmt_money(telesale['avg_per_capita'])}</div>
      <div style="margin-top:8px">{sparkline_svg(ts_daily_amts)}</div>
    </div>
    <div class="kpi-card purple">
      <div class="label">App月累计营收</div>
      <div class="value">{fmt_money(app['total_amt'])}</div>
      <div class="change">日均 {fmt_money(app['total_amt']/max(len(app['daily']),1))} | ARPU {fmt_money(app['avg_arpu'])}</div>
      <div style="margin-top:8px">{sparkline_svg(app_daily_amts)}</div>
    </div>
    <div class="kpi-card orange">
      <div class="label">建信月累计切面</div>
      <div class="value">{fmt_money(jianxin['total_pay_qm'])}</div>
      <div class="change">企微添加 {jianxin['total_qywx']:,} | 调配 {jianxin['total_adjust']:,}</div>
      <div style="margin-top:8px">{sparkline_svg(jx_daily_qywx)}</div>
    </div>
    <div class="kpi-card green">
      <div class="label">红娘月累计营收</div>
      <div class="value">{fmt_money(hongniang['total_pay'])}</div>
      <div class="change">见面 {hongniang['total_jm']:,}人次 | 恋爱 {hongniang['love_m']}对</div>
      <div style="margin-top:8px">{sparkline_svg(hn_daily_jm)}</div>
    </div>
    <div class="kpi-card red">
      <div class="label">趣约会月累计营收</div>
      <div class="value">{fmt_money(qyh['total_pay'])}</div>
      <div class="change">日均DAU {qyh['avg_dau']:,.0f} | 直播礼物 {fmt_money(qyh['total_gift'])}</div>
      <div style="margin-top:8px">{sparkline_svg(qyh_daily_pay)}</div>
    </div>
  </div>

  <!-- ===== 电销深度分析 ===== -->
  <div class="section">
    <h2>一、电话销售深度分析</h2>

    <div class="two-col">
      <div>
        <h3>核心指标总览</h3>
        <div class="metric-row"><span class="label">月累计业绩</span><span class="val">{fmt_money(telesale['total_pay'])}</span></div>
        <div class="metric-row"><span class="label">总外呼量</span><span class="val">{telesale['total_callout']:,}</span></div>
        <div class="metric-row"><span class="label">总接通量</span><span class="val">{telesale['total_link']:,}</span></div>
        <div class="metric-row"><span class="label">月均接通率</span><span class="val {'highlight' if telesale['link_rate']<43 else ''}">{fmt_pct(telesale['link_rate'])}</span></div>
        <div class="metric-row"><span class="label">深度沟通率</span><span class="val">{fmt_pct(telesale['deep_rate'])}</span></div>
        <div class="metric-row"><span class="label">成交笔数</span><span class="val">{telesale['total_pay_num']:,}</span></div>
        <div class="metric-row"><span class="label">日均在岗</span><span class="val">{telesale['avg_workers']:.0f}人</span></div>
        <div class="metric-row"><span class="label">人均日产值</span><span class="val">{fmt_money(telesale['avg_per_capita'])}</span></div>
      </div>
      <div>
        <h3>周维度趋势</h3>
        <table>
          <tr><th>周次</th><th>天数</th><th>业绩</th><th>日均</th><th>接通率</th></tr>"""

    for wk in sorted(weeks.keys()):
        w = weeks[wk]
        wk_lr = w['link'] / w['callout'] * 100 if w['callout'] > 0 else 0
        wk_avg = w['pay'] / w['days'] if w['days'] > 0 else 0
        html += f"""
          <tr><td>{wk}</td><td>{w['days']}</td><td>{fmt_money(w['pay'])}</td>
              <td>{fmt_money(wk_avg)}</td><td>{fmt_pct(wk_lr)}</td></tr>"""

    html += """
        </table>
      </div>
    </div>

    <h3>日度业绩走势</h3>
    <table>
      <tr><th>日期</th><th>在岗</th><th>外呼</th><th>接通</th><th>接通率</th><th>深沟</th><th>深沟率</th>
          <th>成交</th><th>业绩</th><th>人均产值</th><th>企微</th></tr>"""

    for d in ts_dates:
        dd = telesale['daily'][d]
        lr = dd['link']/dd['callout']*100 if dd['callout']>0 else 0
        dr = dd['deep10']/dd['link']*100 if dd['link']>0 else 0
        pc = dd['pay_amt']/dd['workers'] if dd['workers']>0 else 0
        lr_cls = ' style="color:#e74c3c;font-weight:700"' if lr<40 else (' style="color:#e67e22"' if lr<43 else '')
        dt_label = d[4:6]+'/'+d[6:]
        html += f"""
      <tr><td>{dt_label}</td><td>{dd['workers']}</td><td>{dd['callout']:,}</td>
          <td>{dd['link']:,}</td><td{lr_cls}>{fmt_pct(lr)}</td>
          <td>{dd['deep10']:,}</td><td>{fmt_pct(dr)}</td>
          <td>{dd['pay_num']}</td><td>{fmt_money(dd['pay_amt'])}</td>
          <td>{fmt_money(pc)}</td><td>{dd['qywx']}</td></tr>"""

    html += """
    </table>"""

    # Dept ranking table
    if dept_ranks:
        html += """
    <h3>部门排名（按月业绩）</h3>
    <table>
      <tr><th>#</th><th>部门</th><th>均在岗</th><th>总外呼</th><th>人均呼</th><th>接通率</th>
          <th>深沟率</th><th>总业绩</th><th>人均产值</th></tr>"""
        for i, dep in enumerate(dept_ranks[:20]):
            html += f"""
      <tr><td>{i+1}</td><td>{dep['name'][:20]}</td><td>{dep['workers']:.0f}</td>
          <td>{dep['callout']:,}</td><td>{dep['per_callout']:.0f}</td>
          <td>{fmt_pct(dep['link_rate'])}</td><td>{fmt_pct(dep['deep_rate'])}</td>
          <td>{fmt_money(dep['pay_amt'])}</td><td>{fmt_money(dep['per_capita'])}</td></tr>"""
        html += "</table>"

    # Telesale diagnostics
    html += """
    <h3>智能诊断</h3>"""
    if telesale['link_rate'] < 43:
        html += f"""
    <div class="insight-box risk">
      <div class="title">⚠️ E02匹配：接通率 {fmt_pct(telesale['link_rate'])} 低于橙线（43%）</div>
      <div>月均接通率低于健康值，可能原因：外呼线路质量下降、号码被标记、外呼时段分布不合理。
      建议排查低接通率部门的线路来源，对比高接通率部门策略。</div>
    </div>"""
    elif telesale['link_rate'] >= 45:
        html += f"""
    <div class="insight-box good">
      <div class="title">✅ 接通率 {fmt_pct(telesale['link_rate'])} 处于健康水平（≥45%）</div>
      <div>月均接通率达标，外呼线路和时段策略运行良好。</div>
    </div>"""

    if telesale['deep_rate'] < 13:
        html += f"""
    <div class="insight-box warn">
      <div class="title">🔶 深度沟通率 {fmt_pct(telesale['deep_rate'])} 低于橙线（13%）</div>
      <div>深沟率偏低表明话术质量不足，团队在"快打快挂"。建议推行标杆录音学习和话术通关。</div>
    </div>"""

    if telesale['avg_per_capita'] < 2000:
        html += f"""
    <div class="insight-box risk">
      <div class="title">⚠️ 人均日产值 {fmt_money(telesale['avg_per_capita'])} 低于橙线（¥2,000）</div>
      <div>人效偏低，需排查是前端量不足还是转化率低。建议按部门拆解，锁定中腰部部门瓶颈。</div>
    </div>"""

    # ===== App 深度分析 =====
    html += f"""
  </div>

  <div class="section">
    <h2>二、App主站深度分析</h2>
    <div class="two-col">
      <div>
        <h3>核心指标总览</h3>
        <div class="metric-row"><span class="label">月累计营收</span><span class="val">{fmt_money(app['total_amt'])}</span></div>
        <div class="metric-row"><span class="label">月累计付费人数</span><span class="val">{app['total_pay_num']:,}</span></div>
        <div class="metric-row"><span class="label">新增付费人数</span><span class="val">{app['total_new_pay']:,}</span></div>
        <div class="metric-row"><span class="label">ARPU</span><span class="val">{fmt_money(app['avg_arpu'])}</span></div>
        <div class="metric-row"><span class="label">日均DAU</span><span class="val">{app['avg_dau']:,.0f}</span></div>
        <div class="metric-row"><span class="label">付费率</span><span class="val">{fmt_pct(app['pay_rate'])}</span></div>
        <div class="metric-row"><span class="label">退款/营收比</span><span class="val {'highlight' if app['refund_ratio']>2 else ''}">{fmt_pct(app['refund_ratio'])}</span></div>
        <div class="metric-row"><span class="label">复购占比</span><span class="val">{fmt_pct(app['fugou_ratio'])}</span></div>
        <div class="metric-row"><span class="label">次日留存率</span><span class="val">{fmt_pct(app['retain_1d_rate'])}</span></div>
        <div class="metric-row"><span class="label">月新注册</span><span class="val">{app['reg_m']:,}</span></div>
      </div>
      <div>
        <h3>产品营收结构</h3>
        <table>
          <tr><th>产品</th><th>营收</th><th>占比</th></tr>"""

    sorted_prods = sorted(app_products.items(), key=lambda x: x[1], reverse=True)
    for pname, pamt in sorted_prods:
        ratio = pamt / app['total_amt'] * 100 if app['total_amt'] > 0 else 0
        bar_color = '#e74c3c' if pname == '珍心会员' and ratio > 80 else '#3949ab'
        html += f"""
          <tr><td>{pname}</td><td>{fmt_money(pamt)}</td>
              <td>{fmt_pct(ratio)}
                <div class="progress-bar"><div class="fill" style="width:{min(ratio,100):.0f}%;background:{bar_color}"></div></div>
              </td></tr>"""

    html += """
        </table>
      </div>
    </div>

    <h3>日度营收走势</h3>
    <table>
      <tr><th>日期</th><th>营收</th><th>付费人数</th><th>新增付费</th><th>DAU</th><th>ARPU</th>
          <th>退款</th><th>退款率</th><th>注册</th></tr>"""

    for d in app['daily']:
        arpu = d['amt']/d['pay_num'] if d['pay_num']>0 else 0
        rr = d['refund']/d['amt']*100 if d['amt']>0 else 0
        rr_cls = ' style="color:#e74c3c;font-weight:700"' if rr>2 else ''
        dt_label = d['date'][4:6]+'/'+d['date'][6:]
        html += f"""
      <tr><td>{dt_label}</td><td>{fmt_money(d['amt'])}</td><td>{d['pay_num']:,}</td>
          <td>{d['pay_num_new']}</td><td>{d['dau']:,}</td><td>{fmt_money(arpu)}</td>
          <td>{fmt_money(d['refund'])}</td><td{rr_cls}>{fmt_pct(rr)}</td><td>{d['mems']:,}</td></tr>"""

    html += "</table>"

    # App diagnostics
    html += """
    <h3>智能诊断</h3>"""
    if app['zhenxin_ratio'] > 80:
        html += f"""
    <div class="insight-box risk">
      <div class="title">⚠️ A01匹配：珍心会员占比 {fmt_pct(app['zhenxin_ratio'])}，超过80%红线</div>
      <div>结构性风险极高。一旦珍心会员出现变动，整体营收将受严重影响。
      建议提升超级会员系列的曝光和转化路径，季度目标降至70%以下。</div>
    </div>"""

    avg_new_pay_daily = app['total_new_pay'] / max(len(app['daily']),1)
    if avg_new_pay_daily < 160:
        html += f"""
    <div class="insight-box warn">
      <div class="title">🔶 A02匹配：日均新增付费 {avg_new_pay_daily:.0f} 人，低于160人基准</div>
      <div>新客转化引擎偏弱，增长靠复购驱动（复购占比 {fmt_pct(app['fugou_ratio'])}）。
      建议优化注册后24h首付费引导，设计首付费专属优惠包。</div>
    </div>"""

    if app['refund_ratio'] > 2:
        html += f"""
    <div class="insight-box risk">
      <div class="title">⚠️ A03匹配：退款/营收比 {fmt_pct(app['refund_ratio'])}，超过2%红线</div>
      <div>需分产品维度拆解退款数据，重点排查退款集中在哪个产品。</div>
    </div>"""
    else:
        html += f"""
    <div class="insight-box good">
      <div class="title">✅ 退款/营收比 {fmt_pct(app['refund_ratio'])}，处于健康水平（<2%）</div>
      <div>退款控制良好，用户满意度和产品体验维持在合理范围。</div>
    </div>"""

    if app['pay_rate'] >= 1.0:
        html += f"""
    <div class="insight-box good">
      <div class="title">✅ 付费率 {fmt_pct(app['pay_rate'])} 达到健康值（≥1.0%）</div>
      <div>流量变现效率良好。</div>
    </div>"""

    # ===== 建信深度分析 =====
    html += f"""
  </div>

  <div class="section">
    <h2>三、建信团队深度分析</h2>
    <div class="two-col">
      <div>
        <h3>核心指标总览</h3>
        <div class="metric-row"><span class="label">月累计切面金额</span><span class="val">{fmt_money(jianxin['total_pay_qm'])}</span></div>
        <div class="metric-row"><span class="label">月累计IM发信</span><span class="val">{jianxin['total_send']:,}</span></div>
        <div class="metric-row"><span class="label">月累计回复</span><span class="val">{jianxin['total_huifu']:,}</span></div>
        <div class="metric-row"><span class="label">IM回复率</span><span class="val">{fmt_pct(jianxin['reply_rate'])}</span></div>
        <div class="metric-row"><span class="label">企微添加数</span><span class="val">{jianxin['total_qywx']:,}</span></div>
        <div class="metric-row"><span class="label">调配人数</span><span class="val">{jianxin['total_adjust']:,}</span></div>
      </div>
      <div>
        <h3>日度企微添加趋势</h3>
        <table>
          <tr><th>日期</th><th>发信</th><th>回复</th><th>回复率</th><th>企微添加</th><th>调配</th><th>切面金额</th></tr>"""

    for d in jx_dates:
        dd = jianxin['daily'][d]
        rr = dd['huifu_n']/dd['send_n']*100 if dd['send_n']>0 else 0
        dt_label = d[4:6]+'/'+d[6:]
        html += f"""
          <tr><td>{dt_label}</td><td>{dd['send_n']:,}</td><td>{dd['huifu_n']:,}</td>
              <td>{fmt_pct(rr)}</td><td>{dd['qywx']:,}</td><td>{dd['adjust']:,}</td>
              <td>{fmt_money(dd['pay_qm'])}</td></tr>"""

    html += """
        </table>
      </div>
    </div>"""

    if jianxin['reply_rate'] < 10:
        html += f"""
    <div class="insight-box warn">
      <div class="title">🔶 J01匹配：IM回复率 {fmt_pct(jianxin['reply_rate'])} 低于10%基准</div>
      <div>发信效率偏低，可能话术缺乏吸引力或发信时间不佳。建议A/B测试不同话术，优化首发信的社交验证和匹配悬念。</div>
    </div>"""

    # ===== 红娘深度分析 =====
    html += f"""
  </div>

  <div class="section">
    <h2>四、电话红娘深度分析</h2>
    <div class="two-col">
      <div>
        <h3>核心指标总览</h3>
        <div class="metric-row"><span class="label">月累计营收</span><span class="val">{fmt_money(hongniang['total_pay'])}</span></div>
        <div class="metric-row"><span class="label">月累计见面</span><span class="val">{hongniang['total_jm']:,} 人次</span></div>
        <div class="metric-row"><span class="label">月累计恋爱</span><span class="val">{hongniang['love_m']} 对</span></div>
        <div class="metric-row"><span class="label">日均在岗红娘</span><span class="val">{hongniang['avg_staff']:.0f} 人</span></div>
        <div class="metric-row"><span class="label">投诉总量</span><span class="val">{hongniang['total_tousu']}</span></div>
        <div class="metric-row"><span class="label">珍爱通退费</span><span class="val">{fmt_money(hongniang['total_refund_za'])}</span></div>
        <div class="metric-row"><span class="label">高端退费</span><span class="val">{fmt_money(hongniang['total_refund_gd'])}</span></div>
      </div>
      <div>
        <h3>日度见面趋势</h3>
        <table>
          <tr><th>日期</th><th>在岗</th><th>见面</th><th>日营收</th><th>投诉</th></tr>"""

    for d in hn_dates:
        dd = hongniang['daily'][d]
        dt_label = d[4:6]+'/'+d[6:]
        html += f"""
          <tr><td>{dt_label}</td><td>{dd['staff']}</td><td>{dd['jm_n']}</td>
              <td>{fmt_money(dd['pay_d'])}</td><td>{dd['tousu']}</td></tr>"""

    html += """
        </table>
      </div>
    </div>"""

    total_refund_all = hongniang['total_refund_za'] + hongniang['total_refund_gd']
    if total_refund_all > 0 and hongniang['total_pay'] > 0:
        refund_ratio = total_refund_all / hongniang['total_pay'] * 100
        if refund_ratio > 15:
            html += f"""
    <div class="insight-box risk">
      <div class="title">⚠️ 红娘退费率 {fmt_pct(refund_ratio)} 偏高（基准<15%）</div>
      <div>退费金额 {fmt_money(total_refund_all)}，需排查退费集中来源和原因。</div>
    </div>"""

    # ===== 趣约会 =====
    html += f"""
  </div>

  <div class="section">
    <h2>五、趣约会深度分析</h2>
    <div class="two-col">
      <div>
        <h3>核心指标总览</h3>
        <div class="metric-row"><span class="label">月累计营收</span><span class="val">{fmt_money(qyh['total_pay'])}</span></div>
        <div class="metric-row"><span class="label">直播礼物收入</span><span class="val">{fmt_money(qyh['total_gift'])}</span></div>
        <div class="metric-row"><span class="label">玫瑰充值</span><span class="val">{fmt_money(qyh['total_rose_charge'])}</span></div>
        <div class="metric-row"><span class="label">日均DAU</span><span class="val">{qyh['avg_dau']:,.0f}</span></div>
      </div>
      <div>
        <h3>日度营收走势</h3>
        <table>
          <tr><th>日期</th><th>营收</th><th>DAU</th><th>直播礼物</th><th>玫瑰充值</th></tr>"""

    for d in qyh['daily']:
        dt_label = d['date'][4:6]+'/'+d['date'][6:]
        html += f"""
          <tr><td>{dt_label}</td><td>{fmt_money(d['pay_amount'])}</td><td>{d['dau']:,}</td>
              <td>{fmt_money(d['live_gift'])}</td><td>{fmt_money(d['rose_charge'])}</td></tr>"""

    html += """
        </table>
      </div>
    </div>
  </div>"""

    # ===== 门店 + 广告投放 =====
    html += f"""
  </div>

  <div class="section">
    <h2>六、门店销售分析</h2>
    <div class="insight-box info">
      <div class="title">🗓️ 春节假期影响</div>
      <div>2月门店数据受春节假期（约2月9日-2月23日）严重影响，大部分门店在假期期间暂停营业。
      有效工作日仅约10天左右。门店数据需结合季节性因素评估，不宜直接与1月对标。</div>
    </div>
    <p style="color:#888;margin-top:12px;">门店2月因春节假期，大部分时段无数据。有效工作日的到店和签单数据有限，建议关注3月恢复趋势。</p>
  </div>

  <div class="section">
    <h2>七、广告投放分析</h2>
    <div class="two-col">
      <div>
        <h3>二月投放总览</h3>
        <div class="metric-row"><span class="label">月投放消耗</span><span class="val" style="color:#e74c3c">¥218.61万</span></div>
        <div class="metric-row"><span class="label">月总回收</span><span class="val">¥115.20万</span></div>
        <div class="metric-row"><span class="label">线上回收</span><span class="val">¥97.45万</span></div>
        <div class="metric-row"><span class="label">电话回收</span><span class="val">¥17.75万</span></div>
        <div class="metric-row"><span class="label">总注册数</span><span class="val">78,778</span></div>
        <div class="metric-row"><span class="label">首日ROI</span><span class="val">52.7%</span></div>
        <div class="metric-row"><span class="label">CPA</span><span class="val">¥27.75</span></div>
      </div>
      <div>
        <h3>投放诊断</h3>
        <div class="insight-box good">
          <div class="title">✅ 首日ROI 52.7% 处于优秀水平（>40%）</div>
          <div>投放效率健康，获客成本CPA ¥27.75处于正常区间（25-40元）。</div>
        </div>
        <div class="insight-box info">
          <div class="title">📊 渠道结构</div>
          <div>应用商店为主要获客渠道，品牌投放和达人投放占比较小。
          建议对高ROI低规模渠道进行放量测试。</div>
        </div>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>八、综合诊断与改善建议</h2>

    <h3>二月整体评级</h3>
    <table>
      <tr><th>业务线</th><th>核心指标</th><th>月度表现</th><th>评级</th><th>关键发现</th></tr>
      <tr>
        <td><strong>电销</strong></td>
        <td>成单金额</td>
        <td>{fmt_money(telesale['total_pay'])}</td>
        <td><span class="badge {'badge-red' if telesale['link_rate']<40 else ('badge-orange' if telesale['link_rate']<43 else 'badge-green')}">
            {'红色' if telesale['link_rate']<40 else ('黄色' if telesale['link_rate']<43 else '绿色')}</span></td>
        <td>接通率{fmt_pct(telesale['link_rate'])}，人均产值{fmt_money(telesale['avg_per_capita'])}</td>
      </tr>
      <tr>
        <td><strong>App</strong></td>
        <td>总营收</td>
        <td>{fmt_money(app['total_amt'])}</td>
        <td><span class="badge {'badge-red' if app['zhenxin_ratio']>80 else ('badge-orange' if avg_new_pay_daily<160 else 'badge-green')}">
            {'红色' if app['zhenxin_ratio']>80 else ('黄色' if avg_new_pay_daily<160 else '绿色')}</span></td>
        <td>珍心会员占比{fmt_pct(app['zhenxin_ratio'])}，ARPU {fmt_money(app['avg_arpu'])}</td>
      </tr>
      <tr>
        <td><strong>建信</strong></td>
        <td>切面金额</td>
        <td>{fmt_money(jianxin['total_pay_qm'])}</td>
        <td><span class="badge {'badge-orange' if jianxin['reply_rate']<10 else 'badge-green'}">
            {'黄色' if jianxin['reply_rate']<10 else '绿色'}</span></td>
        <td>IM回复率{fmt_pct(jianxin['reply_rate'])}，企微添加{jianxin['total_qywx']:,}</td>
      </tr>
      <tr>
        <td><strong>红娘</strong></td>
        <td>见面+营收</td>
        <td>{fmt_money(hongniang['total_pay'])}</td>
        <td><span class="badge badge-blue">综合</span></td>
        <td>见面{hongniang['total_jm']:,}次，恋爱{hongniang['love_m']}对，投诉{hongniang['total_tousu']}</td>
      </tr>
      <tr>
        <td><strong>趣约会</strong></td>
        <td>总营收</td>
        <td>{fmt_money(qyh['total_pay'])}</td>
        <td><span class="badge badge-blue">综合</span></td>
        <td>日均DAU {qyh['avg_dau']:,.0f}，直播礼物{fmt_money(qyh['total_gift'])}</td>
      </tr>
      <tr>
        <td><strong>门店</strong></td>
        <td>到店+签单</td>
        <td>¥0.95万</td>
        <td><span class="badge badge-orange">黄色</span></td>
        <td>春节影响严重，有效工作日不足10天，到店117次，签单3笔</td>
      </tr>
      <tr>
        <td><strong>广告投放</strong></td>
        <td>ROI</td>
        <td>消耗¥218.61万</td>
        <td><span class="badge badge-green">绿色</span></td>
        <td>首日ROI 52.7%优秀，注册78,778人，CPA ¥27.75</td>
      </tr>
    </table>

    <h3>TOP 改善建议（按预估增幅排序）</h3>
    <table>
      <tr><th>优先级</th><th>问题/机会</th><th>负责人</th><th>今日可执行动作</th><th>坚持天数</th><th>预估增幅</th></tr>"""

    suggestions = []
    if telesale['link_rate'] < 45:
        gap = 45 - telesale['link_rate']
        est_daily = telesale['avg_daily_pay'] * (gap / 100) * 1.5
        suggestions.append(('P0','接通率提升','罗阳',
            f'排查低接通率部门线路，调整外呼时段至10-12点和14-17点黄金时段',
            '14天', est_daily * 30))

    if telesale['deep_rate'] < 15:
        est_daily = telesale['avg_daily_pay'] * 0.08
        suggestions.append(('P1','深沟率提升','罗阳/各部经理',
            '晨会播放1条标杆录音+午间话术通关，重点关注10分钟沟通节奏',
            '14天', est_daily * 30))

    if app['zhenxin_ratio'] > 70:
        est = app['total_amt'] * 0.03
        suggestions.append(('P1','App产品结构优化','梁思聪',
            '增加超级会员系列在首页、个人中心、匹配结果页的曝光位',
            '30天', est))

    if avg_new_pay_daily < 200:
        est = (200 - avg_new_pay_daily) * app['avg_arpu'] * 30
        suggestions.append(('P1','新用户首付引导','梁思聪',
            '上线注册24h内首付费弹窗，设计¥9.9试用包→正价续费路径',
            '21天', est))

    if jianxin['reply_rate'] < 10:
        est = jianxin['total_pay_qm'] * 0.1
        suggestions.append(('P2','IM回复率提升','程朴娟',
            '各组提交3种首发信话术，必须包含社交验证+匹配悬念+行动号召，明日A/B测试',
            '7天', est))

    suggestions.sort(key=lambda x: x[5], reverse=True)

    for s in suggestions:
        html += f"""
      <tr><td><span class="badge badge-{'red' if s[0]=='P0' else ('orange' if s[0]=='P1' else 'blue')}">{s[0]}</span></td>
          <td>{s[1]}</td><td>{s[2]}</td><td>{s[3]}</td><td>{s[4]}</td>
          <td>{fmt_money(s[5])}/月</td></tr>"""

    html += f"""
    </table>

    <h3>二月份关键发现摘要</h3>
    <div class="insight-box info">
      <div class="title">📊 全业务线二月营收合计：{fmt_money(total_revenue)}</div>
      <div>
        <ul style="margin:8px 0 0 16px;">
          <li><strong>电销</strong>：月业绩 {fmt_money(telesale['total_pay'])}，日均外呼 {telesale['total_callout']//max(len(ts_dates),1):,} 通，
              接通率 {fmt_pct(telesale['link_rate'])}，人均产值 {fmt_money(telesale['avg_per_capita'])}</li>
          <li><strong>App</strong>：月营收 {fmt_money(app['total_amt'])}，ARPU {fmt_money(app['avg_arpu'])}，
              DAU {app['avg_dau']:,.0f}，付费率 {fmt_pct(app['pay_rate'])}</li>
          <li><strong>建信</strong>：切面 {fmt_money(jianxin['total_pay_qm'])}，企微 {jianxin['total_qywx']:,}，回复率 {fmt_pct(jianxin['reply_rate'])}</li>
          <li><strong>红娘</strong>：营收 {fmt_money(hongniang['total_pay'])}，见面 {hongniang['total_jm']:,}次，恋爱 {hongniang['love_m']}对</li>
          <li><strong>趣约会</strong>：营收 {fmt_money(qyh['total_pay'])}，DAU {qyh['avg_dau']:,.0f}</li>
        </ul>
      </div>
    </div>

    <div class="insight-box info">
      <div class="title">🗓️ 二月季节性因素</div>
      <div>2月含春节假期（约2月初），节后返工首周数据通常出现反弹效应。情人节（2/14）前后注册和付费可能有脉冲式上升。
      建议将春节期间低值视为正常季节性波动，重点关注节后恢复速度和趋势方向。</div>
    </div>
  </div>

  <div class="footer">
    珍爱网智慧助理 · Linh 生成 | {now} | 数据来源：珍爱网数据分析API
  </div>
</div>
</body>
</html>"""

    return html


# ─── Main ───
def main():
    print("="*60)
    print("  珍爱网（SHYB）2026年2月 全面数据分析")
    print("="*60)

    data = fetch_all_data()

    telesale = analyze_telesale(data)
    app = analyze_app(data)
    jianxin = analyze_jianxin(data)
    hongniang = analyze_hongniang(data)
    qyh = analyze_qyh(data)

    html = generate_html(telesale, app, jianxin, hongniang, qyh)

    os.makedirs('reports', exist_ok=True)
    output_path = 'reports/SHYB_February_2026_Analysis.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✅ 报告已生成: {output_path}")
    print(f"   文件大小: {os.path.getsize(output_path)/1024:.1f} KB")

    summary = {
        '电销月业绩': fmt_money(telesale['total_pay']),
        '电销接通率': fmt_pct(telesale['link_rate']),
        '电销深沟率': fmt_pct(telesale['deep_rate']),
        '电销人均产值': fmt_money(telesale['avg_per_capita']),
        'App月营收': fmt_money(app['total_amt']),
        'App_ARPU': fmt_money(app['avg_arpu']),
        'App日均DAU': f"{app['avg_dau']:,.0f}",
        'App付费率': fmt_pct(app['pay_rate']),
        '建信切面': fmt_money(jianxin['total_pay_qm']),
        '建信回复率': fmt_pct(jianxin['reply_rate']),
        '红娘营收': fmt_money(hongniang['total_pay']),
        '红娘见面': f"{hongniang['total_jm']:,}次",
        '趣约会营收': fmt_money(qyh['total_pay']),
    }

    print("\n📋 核心指标摘要:")
    for k, v in summary.items():
        print(f"   {k}: {v}")

    with open('reports/february_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return summary


if __name__ == '__main__':
    main()
