import os
import json
import datetime
import webbrowser

def generate_mock_data():
    """生成符合手册设定的模拟业务数据"""
    return {
        "report_date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "telemarketing": {
            "total_reps": 120,
            "total_revenue": 3600000,
            "top_20_revenue_pct": 65, # 痛点：TOP20%员工贡献了65%的业绩，方差极大
            "avg_per_capita": 30000,
            "connect_rate": 41 # 痛点：低于43%预警线
        },
        "store_sales": {
            "allocated_leads": 5000,
            "arrived_leads": 600,
            "signed_deals": 70,
            "total_revenue": 1400000, # 客单价2万
            "arrival_rate": 12, # 痛点：低于15%预警线
            "sign_rate": 11.6
        },
        "public_pool": {
            "total_leads": 120000,
            "untouched_over_30d": 85000, # 痛点：大量沉淀
            "timely_entry_rate": 62, # 痛点：低于70%预警线，销售藏单
            "retrieval_conversion_rate": 1.5 # 痛点：低于2%预警线
        },
        "service_quality": {
            "daily_revenue": 800000,
            "daily_refund": 45000, # 痛点：4.5万 > 80万*5% (4万)，触发退费预警
            "refund_rate": 5.6
        },
        "app_health": {
            "total_app_revenue": 2500000,
            "zhenxin_member_revenue": 2100000,
            "zhenxin_pct": 84, # 痛点：>80% 结构单一风险
            "dau_growth": -2.1
        }
    }

def generate_html_report(data):
    """生成精美的HTML诊断报告"""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>珍爱网 CEO 商业运营全景诊断报告</title>
        <style>
            body {{ font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; background-color: #f4f7f9; color: #333; margin: 0; padding: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ background: linear-gradient(135deg, #ff4b4b 0%, #ff2a2a 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .header h1 {{ margin: 0 0 10px 0; font-size: 28px; }}
            .header p {{ margin: 0; opacity: 0.9; font-size: 16px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); gap: 20px; margin-bottom: 20px; }}
            .card {{ background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); border-top: 4px solid #ddd; }}
            .card.warning {{ border-top-color: #ff4b4b; }}
            .card.safe {{ border-top-color: #00c853; }}
            .card h2 {{ margin-top: 0; font-size: 20px; color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
            .metric {{ display: flex; justify-content: space-between; margin-bottom: 15px; font-size: 16px; }}
            .metric .value {{ font-weight: bold; font-size: 18px; }}
            .metric .value.red {{ color: #ff4b4b; }}
            .metric .value.green {{ color: #00c853; }}
            .diagnosis {{ background: #fff3f3; padding: 15px; border-radius: 8px; margin-top: 15px; border-left: 4px solid #ff4b4b; font-size: 14px; line-height: 1.6; color: #d32f2f; }}
            .action {{ background: #f0f7ff; padding: 15px; border-radius: 8px; margin-top: 10px; border-left: 4px solid #2196f3; font-size: 14px; line-height: 1.6; color: #0d47a1; }}
            .footer {{ text-align: center; color: #888; margin-top: 40px; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>珍爱网 CEO 商业运营全景诊断报告</h1>
                <p>生成时间：{data['report_date']} | 数据来源：业务大盘模拟数据 | 诊断标准：《CEO决策全景手册》</p>
            </div>

            <div class="grid">
                <!-- 1. 电销人均业绩 -->
                <div class="card warning">
                    <h2>1. 电销人均业绩诊断 (利润中心)</h2>
                    <div class="metric"><span>总人数</span> <span class="value">{data['telemarketing']['total_reps']} 人</span></div>
                    <div class="metric"><span>人均产值</span> <span class="value">¥{data['telemarketing']['avg_per_capita']:,}</span></div>
                    <div class="metric"><span>TOP20%业绩占比</span> <span class="value red">{data['telemarketing']['top_20_revenue_pct']}% (标准<50%)</span></div>
                    <div class="metric"><span>接通率</span> <span class="value red">{data['telemarketing']['connect_rate']}% (预警线43%)</span></div>
                    
                    <div class="diagnosis">
                        <strong>[E04/E01 异常诊断]</strong><br>
                        1. 业绩高度集中在头部，中腰部产能极低（人效方差极大）。<br>
                        2. 接通率跌破43%红线，存在量换质的不可持续风险。
                    </div>
                    <div class="action">
                        <strong>[CEO 决策建议]</strong><br>
                        1. 强制中腰部员工进行话术通关培训（提升 ai_score）。<br>
                        2. 立即通知罗阳+程朴娟排查线路和号码标记问题。
                    </div>
                </div>

                <!-- 2. 门店资源单条产值 -->
                <div class="card warning">
                    <h2>2. 门店资源单条产值诊断 (高客单)</h2>
                    <div class="metric"><span>分配资源量</span> <span class="value">{data['store_sales']['allocated_leads']} 条</span></div>
                    <div class="metric"><span>单条产值</span> <span class="value">¥{int(data['store_sales']['total_revenue']/data['store_sales']['allocated_leads'])} /条</span></div>
                    <div class="metric"><span>到店率</span> <span class="value red">{data['store_sales']['arrival_rate']}% (预警线15%)</span></div>
                    <div class="metric"><span>到店签单率</span> <span class="value">{data['store_sales']['sign_rate']}%</span></div>
                    
                    <div class="diagnosis">
                        <strong>[D0 损耗诊断]</strong><br>
                        1. 邀约开出率与到店率低于15%预警线，前端流量漏斗严重收缩。<br>
                        2. 邀约团队与门店团队存在博弈，邀约质量下降导致门店单条产值被摊薄。
                    </div>
                    <div class="action">
                        <strong>[CEO 决策建议]</strong><br>
                        1. 建立交叉考核：邀约团队KPI必须绑定“到店签单率”，防止凑量。<br>
                        2. 门店团队考核“接单转化率”，严禁挑肥拣瘦。
                    </div>
                </div>

                <!-- 3. 公海资源浪费情况 -->
                <div class="card warning">
                    <h2>3. 公海资源浪费诊断 (资源回收)</h2>
                    <div class="metric"><span>公海总盘子</span> <span class="value">{data['public_pool']['total_leads']:,} 条</span></div>
                    <div class="metric"><span>沉淀超30天无跟进</span> <span class="value red">{data['public_pool']['untouched_over_30d']:,} 条</span></div>
                    <div class="metric"><span>及时进公海率</span> <span class="value red">{data['public_pool']['timely_entry_rate']}% (预警线70%)</span></div>
                    <div class="metric"><span>捞取转化率</span> <span class="value red">{data['public_pool']['retrieval_conversion_rate']}% (预警线2%)</span></div>
                    
                    <div class="diagnosis">
                        <strong>[隐性利润漏洞诊断]</strong><br>
                        1. 及时进公海率仅62%，说明前端销售存在严重“藏单”行为。<br>
                        2. 超过70%的公海资源沉睡超30天，张心蕊团队捞取转化率不达标。
                    </div>
                    <div class="action">
                        <strong>[CEO 决策建议]</strong><br>
                        1. 强制系统规则：D3-15未成单自动掉落公海，严惩私藏资源。<br>
                        2. 引入AI外呼进行公海初步清洗，洗出意向后再让人工捞取。
                    </div>
                </div>

                <!-- 4. 服务团队质量 -->
                <div class="card warning">
                    <h2>4. 服务团队质量与退费诊断 (底线)</h2>
                    <div class="metric"><span>昨日营收</span> <span class="value">¥{data['service_quality']['daily_revenue']:,}</span></div>
                    <div class="metric"><span>昨日退费</span> <span class="value red">¥{data['service_quality']['daily_refund']:,}</span></div>
                    <div class="metric"><span>退费营收比</span> <span class="value red">{round(data['service_quality']['daily_refund']/data['service_quality']['daily_revenue']*100, 1)}% (红线 5%)</span></div>
                    
                    <div class="diagnosis">
                        <strong>[服务兜底风险诊断]</strong><br>
                        1. 日退费金额已突破日营收的5%红线，服务质量或过度承诺问题凸显。<br>
                        2. 退费杠杆：退费率每降1%，等效营收增长1%。当前处于利润失血状态。
                    </div>
                    <div class="action">
                        <strong>[CEO 决策建议]</strong><br>
                        1. 立即分业务线排查退费原因，严控客诉。<br>
                        2. 检查邀约与门店、建信与电销之间的“部门墙”，是否存在信息断层和过度承诺。
                    </div>
                </div>

                <!-- 5. App 运营健康度 -->
                <div class="card warning">
                    <h2>5. App 运营健康度诊断 (增量引擎)</h2>
                    <div class="metric"><span>App总营收</span> <span class="value">¥{data['app_health']['total_app_revenue']:,}</span></div>
                    <div class="metric"><span>珍心会员收入占比</span> <span class="value red">{data['app_health']['zhenxin_pct']}% (红线 80%)</span></div>
                    <div class="metric"><span>DAU 日环比</span> <span class="value red">{data['app_health']['dau_growth']}%</span></div>
                    
                    <div class="diagnosis">
                        <strong>[A01 结构风险诊断]</strong><br>
                        1. 珍心会员收入占比高达84%，变现结构极度单一，抗风险能力弱。<br>
                        2. DAU出现下滑趋势，说明纯荷尔蒙社交或匹配效率遇到瓶颈。
                    </div>
                    <div class="action">
                        <strong>[CEO 决策建议]</strong><br>
                        1. 必须把珍心会员占比压降到70%以下。<br>
                        2. 大力发展“趣约会”直播打赏、增值虚拟商品等非会员收入，拉高单客ARPU。
                    </div>
                </div>
            </div>
            
            <div class="footer">
                <p>本系统基于《珍爱网商业运营与CEO决策全景手册》重构 | 自动化单脚本闭环运行</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    report_path = os.path.join(os.getcwd(), "CEO_Business_Diagnosis_Report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"报告已生成: {report_path}")
    return report_path

if __name__ == "__main__":
    print("正在初始化珍爱网商业运营数据引擎...")
    data = generate_mock_data()
    print("正在进行全景业务诊断...")
    report_file = generate_html_report(data)
    print("正在打开诊断报告...")
    webbrowser.open('file://' + os.path.realpath(report_file))
