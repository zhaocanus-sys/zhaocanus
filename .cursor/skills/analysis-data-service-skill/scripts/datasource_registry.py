#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源注册表 — 15 个业务域 → 130+ 张业务表

所有表已统一迁移到 CynosDB：
  - compass_data：业务分析表（120+ 张）
"""
from typing import List, Dict, Optional, Tuple


DATASOURCE_REGISTRY: Dict[str, dict] = {

    # ── 电销 ──
    "telesale": {
        "database": "compass_data",
        "label": "电话销售",
        "tables": {
            "ads_za_crm_telsale_day_report_group_d": "电销日报、组维度",
            "ads_za_crm_telsale_hour_report_group_worker_d": "电销小时报、组+员工、日分区",
            "ads_za_crm_telsale_hour_report_group_worker": "电销小时报、组+员工",
            "ads_za_crm_telsale_hour_report_group": "电销小时报、组维度",
            "ads_za_offline_dx_trans_worker_d_all": "电销转化、员工维度",
            "ads_za_crm_dx_fuwu_report_d_all": "电销服务报表",
            "ads_za_crm_worker_dx_fuwu_report_d_all": "红娘员工电销服务报表",
            "ads_za_offline_tel_allot_call_pay_d_all": "电销资源分配拨打付费、资源转化漏斗、资源评级",
            "ads_za_crm_telesell_service_daily_d_all": "电话红娘服务日报",
            "f_online_dianxiao_daily20190326_d": "线上电销日报",
            "DetailTelSellResult": "电销结果",
            "DetailTelSellRefund": "电销退费",
            "DetailTelSellAccumulate": "电销累计业绩",
        },
    },

    # ── 建信 ──
    "jianxin": {
        "database": "compass_data",
        "label": "建信",
        "tables": {
            "ads_za_offline_tel_operation_report_d": "建信日报、电话运营",
            "ads_za_offline_tel_operation_report_worker_d": "建信员工日报",
            "ads_za_offline_tel_operation_report_worker_h": "建信员工小时报",
            "ads_za_offline_tel_operation_report_h": "建信小时报",
            "dwd_za_offline_tel_net_adjusthistory_pay_d_all": "建信团队转出资源付费转化、转出会员明细、含转出/接收员工及部门、付费时间与金额",
        },
    },

    # ── 邀约 ──
    "invite": {
        "database": "compass_data",
        "label": "邀约",
        "tables": {
            "ads_za_offline_invite_data_monitoring_result_d": "邀约数据监控",
            "ads_za_offline_allot_call_d": "邀约分配来电",
            "ads_za_offline_invite_hourly_report_worker_leave_d": "邀约员工小时报（含请假）",
            "DetailInviteRefund": "邀约退费",
            "DetailInviteAllot": "邀约分配",
            "DetailInviteOrder": "邀约订单",
            "DetailArrivalShop": "到店明细",
        },
    },

    # ── 门店 ──
    "shop": {
        "database": "compass_data",
        "label": "门店",
        "tables": {
            "ads_za_crm_saleworker_report_1d_result": "门店销售员工日报",
            "ads_za_offline_newmode_shop_report_d": "新模式门店日报",
            "ads_za_offline_realpay_target_d": "门店实付目标",
            "ads_za_offline_realpay_cost_d": "城市切面实付成本",
            "DetailSaleOrder": "销售订单明细、销售业绩",
            "DetailSaleNormalRefund": "销售常规退费",
            "DetailManagerSaleOrder": "经理销售订单",
            "DetailManagerSaleRefund": "经理销售退费",
            "DetailSaleOrderFinish": "销售订单完成",
            "DetailSaleOrderFinishRefund": "销售订单完成退费",
        },
    },

    # ── 红娘 ──
    "hongniang": {
        "database": "compass_data",
        "label": "红娘",
        "tables": {
            "ads_za_offline_meet_push_base_info_new_d_all": "见面推荐基础信息",
            "ads_za_offline_meet_push_d": "红娘见面推荐日报",
            "ads_za_offline_marriage_zhenaitong_vip_period_d_all": "珍爱通VIP周期",
            "ads_res_tel_service_fuwu_d": "电话服务日报",
            "ads_res_tel_service_jm_tj_d": "电话服务金牌推荐",
            "DetailMatchmakerRefund": "红娘退费",
            "DetailMatchmakerMeetCoverRateBaseInfo": "红娘见面覆盖率",
            "DetailMatchmakerManagerLove": "红娘经理牵手",
            "DetailMatchmakerLove": "红娘牵手",
            "DetailMatchmakerBigOrderMeet": "红娘大单见面",
            "DetailMatchmakerFinishOrder": "红娘完成订单",
            "DetailMatchmakerFinishOrderInfo": "红娘完成订单信息",
            "DetailTelMatchmakerRefund": "电话红娘退费",
            "DetailTelMatchmakerManagerPerformanceSummary": "电话红娘经理业绩汇总",
            "DetailTelMatchmakerManagerPerformance": "电话红娘经理业绩",
            "DetailTelMatchmakerPerformance": "电话红娘业绩",
            "DetailTelMatchmakerMeetAndLove": "电话红娘见面与牵手",
            "DetailTelMatchmakerMeetMotivate": "电话红娘见面激励",
            "dws_za_offline_servicecontact_d_all": "电话红娘服务联系/跟进明细表，含VIP/会员跟进记录、联系方式、跟进状态等信息",
        },
    },

    # ── App / 互联网 ──
    "app": {
        "database": "compass_data",
        "label": "App主站",
        "tables": {
            "ads_za_app_user_order_stats_d": "App用户订单统计",
            "ads_za_app_revenue_order_d_all": "App收入订单",
            "ads_za_app_revenue_pay_d_all": "珍爱主站收入、含珍心会员/珍爱币/超级提醒/超级会员等产品的付费人数及付费金额",
            "r_app_act_reg_pay_d": "App活跃注册付费",
            "ads_za_app_aiask_traffic_acq_quality_d_all": "App AI问答流量获取质量",
            "f_offline_service_detail": "线下服务明细",
            "d_offline_dayoff": "线下休假记录",
        },
    },

    # ── 趣约会 ──
    "qyh": {
        "database": "compass_data",
        "label": "趣约会",
        "tables": {
            "r_qyh_active_m": "趣约会月活跃",
            "ads_qyh_ad_daily_ad_cost_d": "趣约会每日投放消耗数据",
            "ads_qyh_ad_roi_d_all": "趣约会投放ROI",
            "ads_qyh_ad_newreg_transform_new_d_all": "趣约会每日注册转化",
            "ads_qyh_ad_financial_month_d": "趣约会投放月累计",
            "t_qyh_toufang_channel_revenue_all_d": "趣约会各渠道收入",
        },
    },

    # ── 幸福汇 ──
    "xfh": {
        "database": "compass_data",
        "label": "幸福汇",
        "tables": {
            "ads_za_offline_data_center_allot_d": "幸福汇分配日报",
            "ads_za_xfh_user_allot_call_pay_d_all": "幸福汇用户分配来电付费",
            "ads_za_offline_data_center_pay_d": "幸福汇付费日报",
            "ads_za_offline_data_center_allot_call_pay_d": "幸福汇当日分配来电付费",
            "ads_za_offline_data_center_allot_call_pay_7day_d": "幸福汇7日分配来电付费",
            "ads_za_xfh_ad_memberreg_pay_daily_d": "幸福汇广告注册付费日报",
        },
    },

    # ── 广告投放 ──
    "advertising": {
        "database": "compass_data",
        "label": "广告投放",
        "tables": {
            "ads_za_ad_conversion_index_daily_d_all": "投放回本日数据、广告转化指标",
            "ads_za_ad_conversion_index_month_m_all": "投放回本月数据",
            "ads_za_ad_consume_effect_day_d": "珍爱渠道投放消耗数据、含珍爱小程序/珍爱通投/珍爱定投/应用商店等渠道每日消耗金额及注册用户数",
            "ads_seed_pomatch_line_consume_effect_day_d_all": "父母牵线渠道投放消耗日报、含渠道/消耗金额及注册用户数",
            "dws_toufang_month_progress_m": "投放月度进度累计",
            "ads_za_ad_reg_pay_new_d": "APP投放注册业绩",
            "ads_ad_reg_allot_trans_d": "线下月累计转化（同周期）",
            "ads_ad_reg_allot_trans_workday_d": "线下月累计转化（同工作日）",
            "ads_za_ad_reg_hour_h": "投放注册小时报",
            "ads_za_ad_targeting_cost_trans_d": "定投城市月累计",
            "ads_za_ad_reg_effect_d": "投放注册日报效果",
            "ads_za_offline_reg_allot_monitoring_d": "城市资源分配监控",
            "ads_za_offline_reg_allot_monitoring_new_d": "城市资源分配监控（新）",
            "ads_za_ad_toufang_channel_revenue_d": "各渠道切面收入",
            "ads_ad_daily_report_d_all": "投放日报",
            "ads_za_ad_source_quality_monitor_d_all": "资源生命周期转化、来源质量监控",
            "ads_ad_reg_allot_rate_d_all": "线下转化情况、注册分配率",
            "ads_za_ad_nosanme_nature_media_d_all": "大通投月度监控、非三方自然媒体",
            "ads_za_ad_reg_platform_pro_d": "投放注册平台分布",
            "ads_za_offline_netsale_channel_conversion_d": "网销渠道转化",
        },
    },


    # ── 退费 ──
    "refund": {
        "database": "compass_data",
        "label": "退费",
        "tables": {
            "ads_offline_service_refundinfo2_d_all": "退费信息明细",
            "r_dept_operation_refund_month_d": "部门退费月报",
            "r_dept_refund_kpi_m": "部门退费KPI",
            "refund_apply_record": "退费申请记录",
            "DirectRefundRecord": "直接退费记录",
        },
    },

    # ── 银发 ──
    "yf": {
        "database": "compass_data",
        "label": "银发",
        "tables": {
            "ads_venus_act_summary_d": "父母牵线、靠近交友、父母为媒每日注册人数、活跃人数、付费人数、付费金额及月累计注册人数、活跃人数、付费人数、付费金额数据",
        },
    },

    # ── 业绩团队 ──
    "performance": {
        "database": "compass_data",
        "label": "业绩团队",
        "tables": {
            "DetailSaleOrder": "销售订单明细、销售业绩",
            "DetailSaleNormalRefund": "销售常规退费",
            "DetailManagerSaleOrder": "经理销售订单",
            "DetailManagerSaleRefund": "经理销售退费",
            "DetailSaleOrderFinish": "销售订单完成",
            "DetailSaleOrderFinishRefund": "销售订单完成退费",
            "DetailInviteRefund": "邀约退费",
            "DetailInviteAllot": "邀约分配",
            "DetailArrivalShop": "到店明细",
            "DetailInviteOrder": "邀约订单",
            "DetailMatchmakerRefund": "红娘退费",
            "DetailMatchmakerMeetCoverRateBaseInfo": "红娘见面覆盖率",
            "DetailMatchmakerManagerLove": "红娘经理牵手",
            "DetailMatchmakerLove": "红娘牵手",
            "DetailMatchmakerBigOrderMeet": "红娘大单见面",
            "DetailMatchmakerFinishOrder": "红娘完成订单",
            "DetailMatchmakerFinishOrderInfo": "红娘完成订单信息",
            "DetailTelSellResult": "电销结果",
            "DetailTelSellRefund": "电销退费",
            "DetailTelSellAccumulate": "电销累计业绩",
            "DetailTelMatchmakerRefund": "电话红娘退费",
            "DetailTelMatchmakerManagerPerformanceSummary": "电话红娘经理业绩汇总",
            "DetailTelMatchmakerManagerPerformance": "电话红娘经理业绩",
            "DetailTelMatchmakerPerformance": "电话红娘业绩",
            "DetailVipComment": "VIP评价",
            "DetailTelMatchmakerMeetAndLove": "电话红娘见面与牵手",
            "DetailTelMatchmakerMeetMotivate": "电话红娘见面激励",
            "DetailInnovationVipMeetAchieve": "创新VIP见面达成",
            "DetailEmotion": "情感签单",
        },
    },

    # ── 罗盘元数据 ──
    "compass_meta": {
        "database": "compass_data",
        "label": "罗盘元数据",
        "tables": {
            "cd_analysises": "罗盘报告明细表，含珍爱/银发所有报告id、报告名称、是否在线等信息",
            "cd_reports": "罗盘报表明细表，含珍爱/银发所有报表id、报表名称、是否在线等信息",
            "cd_book_emails": "罗盘邮件发送配置信息，含推送的邮件id、邮件名称、是否在线及推送时间等信息",
            "cd_robot": "罗盘机器人推送配置信息表，含所有机器人推送任务相关信息",
            "cd_robot_task": "罗盘机器人推送任务列表，含推送的报表/报告、上次推送时间及下次预计推送时间等信息",
            "r_compass_log_report_d": "珍爱业务罗盘报表浏览记录，反映当前罗盘报表是否有人在关注",
            "ads_meta_seed_compass_log_report_d": "银发业务罗盘报表浏览记录，反映当前罗盘报表是否有人在关注",
        },
    },

    # ── CRM 组织架构 ──
    "crm": {
        "database": "compass_data",
        "label": "CRM组织架构",
        "tables": {
            "Dept": "部门表、组织架构",
            "Worker": "员工表、人员信息",
            "SaleCase": "VIP用户、销售案例、成熟度",
            "member_core_info_daily": "会员核心信息日表、活跃用户",
            "AllotHistory": "分配明细、分配历史（电销/建信）",
            "dwd_za_offline_dx_allot_vip_d": "电销分配VIP明细",
            "dwd_za_offline_dalilypaydetail_d_all": "日付费明细",
            "ads_offline_sale_yunying_yuebao_m": "销售运营月报",
            "CrmSendSMS": "短信记录发送表、CRM短信发送明细",
        },
    },
}

# ── 反向索引：表名 → (source_key, database) ──
_TABLE_INDEX: Dict[str, Tuple[str, str]] = {}
for _src_key, _src_info in DATASOURCE_REGISTRY.items():
    for _tbl in _src_info["tables"]:
        _TABLE_INDEX[_tbl] = (_src_key, _src_info["database"])


def list_sources() -> List[dict]:
    """列出所有业务域"""
    result = []
    for key, info in DATASOURCE_REGISTRY.items():
        result.append({
            "key": key,
            "label": info["label"],
            "database": info["database"],
            "table_count": len(info["tables"]),
        })
    return result


def list_tables(source_key: str) -> List[dict]:
    """列出某业务域下的所有表"""
    src = DATASOURCE_REGISTRY.get(source_key)
    if not src:
        return []
    result = []
    for table_name, keywords in src["tables"].items():
        result.append({
            "table": table_name,
            "database": src["database"],
            "keywords": keywords,
        })
    return result


def find_table(keyword: str) -> List[dict]:
    """按业务关键词模糊匹配找表"""
    results = []
    kw_lower = keyword.lower()
    for src_key, src_info in DATASOURCE_REGISTRY.items():
        for table_name, table_keywords in src_info["tables"].items():
            if kw_lower in table_keywords.lower() or kw_lower in table_name.lower():
                results.append({
                    "source": src_key,
                    "source_label": src_info["label"],
                    "database": src_info["database"],
                    "table": table_name,
                    "keywords": table_keywords,
                })
    return results


def resolve_table(table_name: str) -> Optional[Tuple[str, str, str]]:
    """通过表名查找所属的 (source_key, database, keywords)"""
    entry = _TABLE_INDEX.get(table_name)
    if not entry:
        return None
    src_key, database = entry
    keywords = DATASOURCE_REGISTRY[src_key]["tables"][table_name]
    return src_key, database, keywords


def get_database_for_table(table_name: str) -> Optional[str]:
    """通过表名获取所在数据库"""
    entry = _TABLE_INDEX.get(table_name)
    return entry[1] if entry else None
