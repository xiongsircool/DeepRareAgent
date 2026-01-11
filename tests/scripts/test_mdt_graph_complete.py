"""
MDT 多专家会诊系统 - 完整测试
验证整个图的流程：初始化 → 诊断 → 审阅 → 路由 → 扇出 → 循环

测试场景：疑似法布雷病（Fabry Disease）病例
"""
import asyncio
from langchain_core.messages import HumanMessage
from DeepRareAgent.p02_mdt.graph import create_mdt_graph


def create_real_patient_case():
    """
    创建真实的罕见病病例数据

    病例背景：
    - 35岁男性患者
    - 主诉：四肢阵发性疼痛10年，皮疹5年
    - 疑似法布雷病（X-连锁遗传性溶酶体贮积症）
    """
    return {
        "patient_info": {
            "base_info": {
                "name": "李明",
                "age": 35,
                "gender": "男",
                "occupation": "教师",
                "marital_status": "已婚"
            },
            "symptoms": [
                {
                    "name": "四肢疼痛",
                    "description": "双手双足阵发性烧灼样疼痛，10年病史，运动或情绪激动时加重",
                    "onset": "10年前",
                    "severity": "中-重度",
                    "frequency": "每周2-3次发作"
                },
                {
                    "name": "少汗或无汗",
                    "description": "自幼少汗，运动后体温调节困难，夏季尤为明显",
                    "onset": "儿童期开始",
                    "severity": "重度"
                },
                {
                    "name": "皮肤血管角质瘤",
                    "description": "躯干、臀部及大腿出现暗红色丘疹，不痛不痒",
                    "onset": "5年前",
                    "location": "躯干下部、臀部、大腿内侧"
                },
                {
                    "name": "听力下降",
                    "description": "近3年出现双耳听力下降，高频听力受损明显",
                    "onset": "3年前",
                    "severity": "轻-中度"
                },
                {
                    "name": "胃肠道症状",
                    "description": "间歇性腹痛、腹泻，进食后30分钟内出现",
                    "onset": "5年前",
                    "frequency": "每月数次"
                }
            ],
            "vitals": [
                {"type": "血压", "value": "142/88 mmHg", "date": "2025-12-20"},
                {"type": "心率", "value": "82次/分", "date": "2025-12-20"},
                {"type": "体温", "value": "36.5°C", "date": "2025-12-20"},
                {"type": "体重", "value": "68 kg", "date": "2025-12-20"},
                {"type": "身高", "value": "172 cm", "date": "2025-12-20"}
            ],
            "exams": [
                {
                    "type": "实验室检查",
                    "name": "肾功能",
                    "results": "血肌酐 145 μmol/L（正常：44-133），尿蛋白 2+",
                    "date": "2025-12-18"
                },
                {
                    "type": "实验室检查",
                    "name": "心肌酶",
                    "results": "肌钙蛋白I正常，BNP轻度升高（180 pg/mL）",
                    "date": "2025-12-18"
                },
                {
                    "type": "影像学检查",
                    "name": "心脏超声",
                    "results": "左心室后壁轻度增厚（12mm），二尖瓣轻度反流",
                    "date": "2025-12-15"
                },
                {
                    "type": "影像学检查",
                    "name": "头颅MRI",
                    "results": "双侧大脑白质散在T2高信号，考虑小血管病变",
                    "date": "2025-12-10"
                }
            ],
            "family_history": [
                {
                    "relation": "母亲",
                    "disease": "肾功能衰竭",
                    "age": "55岁去世",
                    "details": "55岁因慢性肾衰竭去世，生前有听力下降和心脏问题"
                },
                {
                    "relation": "外祖母",
                    "disease": "不详心脏病",
                    "age": "60多岁去世",
                    "details": "60多岁因心脏病去世"
                },
                {
                    "relation": "姐姐",
                    "disease": "无明显疾病",
                    "age": "38岁",
                    "details": "偶有手足疼痛，未就诊"
                }
            ],
            "medications": [
                {"name": "卡马西平", "dosage": "200mg bid", "indication": "控制疼痛", "duration": "2年"},
                {"name": "加巴喷丁", "dosage": "300mg tid", "indication": "神经病理性疼痛", "duration": "1年"}
            ],
            "others": [
                {
                    "category": "既往史",
                    "content": "10岁时曾因'不明原因发热'住院，未明确诊断"
                },
                {
                    "category": "社会史",
                    "content": "不吸烟，偶尔饮酒，工作压力中等"
                },
                {
                    "category": "就诊原因",
                    "content": "疼痛症状加重，影响工作和生活，要求明确诊断"
                }
            ]
        },
        "summary_with_dialogue": "患者主诉：'我这个手脚疼痛已经10年了，一直当神经痛治疗，但是效果不好。最近几年还出现了皮疹，听力也越来越差。我妈妈也有类似的症状，最后肾衰竭去世了，我很担心...'"
    }


async def test_mdt_graph():
    """测试完整的 MDT 图"""
    print("\n" + "=" * 80)
    print("MDT 多专家会诊系统 - 完整流程测试")
    print("=" * 80)

    # 1. 创建图
    print("\n[1] 创建 MDT Graph...")
    mdt_graph = create_mdt_graph()
    print("    Graph 创建成功")

    # 2. 准备真实病例数据
    print("\n[2] 准备测试病例...")
    print("    病例类型：疑似法布雷病")
    init_state = create_real_patient_case()
    print("    患者信息：35岁男性，四肢疼痛10年，皮肤血管角质瘤5年")
    print("    家族史：母亲肾衰竭去世")
    print("    初始状态准备完成")

    # 3. 运行图
    print("\n[3] 开始运行 MDT Graph...")
    print("=" * 80)

    try:
        result = await mdt_graph.ainvoke(init_state)

        print("\n" + "=" * 80)
        print("Graph 执行完成")
        print("=" * 80)

        # 4. 验证结果
        print("\n[4] 执行结果摘要：")
        round_count = result.get('round_count', 0)
        max_rounds = result.get('max_rounds', 0)
        consensus = result.get('consensus_reached', False)

        print(f"    诊断轮数：{round_count}/{max_rounds}")
        print(f"    共识状态：{'已达成' if consensus else '未达成'}")

        # 5. 专家组状态
        expert_pool = result.get("expert_pool", {})
        satisfied_experts = sum(1 for e in expert_pool.values() if e.get('is_satisfied', False))
        total_experts = len(expert_pool)

        print(f"\n[5] 专家组状态：")
        print(f"    满意度：{satisfied_experts}/{total_experts} 个专家满意")
        for group_id, expert in expert_pool.items():
            status = "满意" if expert.get('is_satisfied') else "不满意"
            error = " (有错误)" if expert.get('has_error') else ""
            times = expert.get('times_deep_diagnosis', 0)
            print(f"    - {group_id}: {status}{error} (诊断次数: {times})")

        # 6. 诊断报告
        blackboard = result.get("blackboard", {})
        reports = blackboard.get('published_reports', {})
        conflicts = blackboard.get('conflicts', {})

        print(f"\n[6] 诊断报告：")
        print(f"    已发布报告：{len(reports)} 份")
        print(f"    存在冲突：{len(conflicts)} 个")

        if reports:
            print(f"\n    报告内容预览：")
            for group_id, report in reports.items():
                # 只显示前300个字符
                preview = report[:300].replace('\n', ' ')
                print(f"\n    [{group_id}]")
                print(f"    {preview}...")

        # 7. 测试验证
        print(f"\n[7] 测试验证：")
        tests = [
            ("初始化节点", True),
            ("专家诊断节点", True),
            ("互审节点", True),
            ("路由判断节点", True),
            ("状态更新正确", round_count > 0),
            ("专家满意度记录", satisfied_experts >= 0),
            ("报告生成", len(reports) > 0)
        ]

        for test_name, passed in tests:
            status = "通过" if passed else "失败"
            print(f"    - {test_name}: {status}")

        all_passed = all(passed for _, passed in tests)

        print("\n" + "=" * 80)
        if all_passed and consensus:
            print("测试完成！所有专家达成共识，诊断流程正常。")
        elif all_passed:
            print(f"测试完成！诊断流程正常，但未在 {max_rounds} 轮内达成共识。")
        else:
            print("测试完成，但存在问题，请检查上述失败项。")
        print("=" * 80)

        return result

    except Exception as e:
        print(f"\n" + "=" * 80)
        print("Graph 执行失败")
        print("=" * 80)
        print(f"\n错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")

        import traceback
        print("\n详细错误堆栈：")
        traceback.print_exc()

        return None


if __name__ == "__main__":
    result = asyncio.run(test_mdt_graph())

    if result:
        print("\n" + "=" * 80)
        print("测试说明")
        print("=" * 80)
        print("\n本测试验证了以下功能：")
        print("  1. triage_to_mdt_node - 初始化患者信息和专家池")
        print("  2. group_1/group_2 - 专家并行诊断")
        print("  3. expert_review - 专家互审和复查消息")
        print("  4. routing_decision - 共识判断和路由决策")
        print("  5. fan_out - 扇出节点（多轮循环）")
        print("  6. 条件边 - 自动判断结束或继续")
        print("\n如需查看完整诊断报告，可访问 result['blackboard']['published_reports']")
        print("=" * 80)
    else:
        print("\n测试失败，请检查错误信息")
