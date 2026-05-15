import streamlit as st
import pandas as pd
import joblib
from datetime import datetime

# =========================
# 모델 불러오기
# =========================

model = joblib.load("ev_charging_model.pkl")

# =========================
# 데이터 불러오기
# =========================

hourly_avg_load = pd.read_csv(
    "hourly_average_load.csv"
)

hourly_fee = pd.read_csv(
    "hourly_average_fee.csv"
)

avg_speed = pd.read_csv(
    "average_charging_speed.csv"
)

processed_load = pd.read_csv(
    "processed_load_level.csv"
)

# =========================
# 페이지 설정
# =========================

st.set_page_config(
    page_title="EV Charging AI",
    page_icon="🔋",
    layout="centered"
)

st.title("🔋 EV 스마트 충전 추천 AI")

st.markdown(
    """
현재 전력 피크, 충전 혼잡도,
충전 요금, 외기온도를 고려하여
최적 충전 시간을 추천합니다.
"""
)

# =========================
# 부하 판단 함수
# =========================

processed_load['start_hour'] = (
    processed_load['시작시간']
    .str.split(':')
    .str[0]
    .astype(int)
)

processed_load['end_hour'] = (
    processed_load['종료시간']
    .str.split(':')
    .str[0]
    .astype(int)
)

def get_load_level(current_hour, current_month):

    for _, row in processed_load.iterrows():

        if row['부하구분명'] == '부하구분없음':
            continue

        month_match = (
            row['시작월']
            <= current_month
            <= row['종료월']
        )

        hour_match = (
            row['start_hour']
            <= current_hour
            <= row['end_hour']
        )

        if month_match and hour_match:
            return row['부하구분명']

    return "중간부하"


def load_level_to_score(load_level):

    if load_level == '경부하':
        return 0

    elif load_level == '중간부하':
        return 1

    elif load_level == '최대부하':
        return 2

    else:
        return 1

# =========================
# 사용자 입력
# =========================

st.header("🚗 차량 상태 입력")

soc_now = st.number_input(
    "현재 배터리 잔량 (%)",
    min_value=0,
    max_value=100,
    value=40
)

target_soc = st.number_input(
    "목표 충전량 (%)",
    min_value=50,
    max_value=100,
    value=80
)

charging_type_text = st.selectbox(
    "충전 방식",
    ['급속', '완속']
)

departure_time = st.selectbox(
    "충전 시작 시간",
    list(range(0, 24)),
    index=8
)

outside_temperature = st.number_input(
    "바깥 온도 (°C)",
    min_value=-20,
    max_value=50,
    value=25
)

# =========================
# 현재 시간 정보
# =========================

now = datetime.now()

# 사용자가 선택한 시간 사용
current_hour = departure_time

current_month = now.month

# =========================
# 부하 점수 계산
# =========================

load_level = get_load_level(
    current_hour,
    current_month
)

load_score = load_level_to_score(
    load_level
)

# =========================
# 충전 혼잡도 조회
# =========================

load_result = hourly_avg_load[

    (hourly_avg_load['hour']
     == current_hour)

    &

    (hourly_avg_load['충전방식']
     == charging_type_text)
]

if len(load_result) > 0:

    charging_load = load_result[
        'charging_load'
    ].values[0]

else:

    charging_load = 0

# =========================
# 충전 요금 조회
# =========================

fee_result = hourly_fee[

    (hourly_fee['hour']
     == current_hour)

    &

    (hourly_fee['charging_type']
     == charging_type_text)
]

if len(fee_result) > 0:

    charging_fee = fee_result[
        '충전요금(합계) (charging_fee)'
    ].values[0]

else:

    charging_fee = 0

# =========================
# 충전 속도 조회
# =========================

speed_result = avg_speed[

    avg_speed[
        '계량기 타입 (meter_type)'
    ]
    .str.contains(charging_type_text)
]

if len(speed_result) > 0:

    charging_speed = speed_result[
        'charging_speed_kwh_per_hour'
    ].values[0]

else:

    charging_speed = 0

# =========================
# ML 입력 생성
# =========================

charging_type = 1 if charging_type_text == '급속' else 0

input_data = pd.DataFrame({

    'soc_now': [soc_now],

    'current_hour': [current_hour],

    'current_month': [current_month],

    'outside_temperature':
        [outside_temperature],

    'charging_type':
        [charging_type],

    'target_soc':
        [target_soc],

    'load_score':
        [load_score],

    'charging_load':
        [charging_load],

    'charging_fee':
        [charging_fee],

    'charging_speed':
        [charging_speed]
})

# =========================
# 예측
# =========================

if st.button("AI 충전 추천 받기"):

    prediction = float(

        model.predict(
            input_data
        )[0]

    )

    prediction = round(
        prediction,
        1
    )

    # =========================
    # 추천 충전 시간 계산
    # =========================

    recommended_hour = (
        current_hour + int(prediction)
    ) % 24
# =========================
# 추천 시간대 혼잡도 조회
# =========================

recommended_load_result = hourly_avg_load[

    (hourly_avg_load['hour']
     == recommended_hour)

    &

    (hourly_avg_load['충전방식']
     == charging_type_text)
]

if len(recommended_load_result) > 0:

    recommended_load = (
        recommended_load_result[
            'charging_load'
        ].values[0]
    )

else:

    recommended_load = charging_load
# =========================
# 추천 시간대 요금 조회
# =========================

recommended_fee_result = hourly_fee[

    (hourly_fee['hour']
     == recommended_hour)

    &

    (hourly_fee['charging_type']
     == charging_type_text)
]

if len(recommended_fee_result) > 0:

    recommended_fee = (
        recommended_fee_result[
            '충전요금(합계) (charging_fee)'
        ].values[0]
    )

else:

    recommended_fee = charging_fee
# =========================
# 효과 계산
# =========================

peak_reduction = (
    (
        charging_load
        - recommended_load
    )
    / charging_load
) * 100

cost_saving = (
    (
        charging_fee
        - recommended_fee
    )
    / charging_fee
) * 100

peak_reduction = round(
    peak_reduction,
    1
)

cost_saving = round(
    cost_saving,
    1
)

st.success(
        f"추천 충전 시작 시간: 약 {prediction}시간 뒤"
    )
st.write(
    f"예상 전력 피크 감소 효과: "
    f"{peak_reduction}%"
)

st.write(
    f"예상 충전요금 절감 효과: "
    f"{cost_saving}%"
)

st.subheader("📊 충전 환경 분석")

if load_score == 2:

    st.warning(
        "⚠ 최대부하 시간대"
    )

elif load_score == 1:

    st.info(
        "중간부하 시간대"
    )

else:

    st.success(
        "경부하 시간대"
    )

# 혼잡도 판단
if charging_load > 15000:

    st.warning(
        "⚠ 충전 혼잡도 높음"
    )

elif charging_load > 8000:

    st.info(
        "충전 혼잡도 보통"
    )

else:

    st.success(
        "충전 혼잡도 낮음"
    )

# 요금 판단
# 요금 판단
if charging_fee > 15000:

    fee_message = "높은 요금"

    st.warning(
        "💰 충전요금 높음"
    )

elif charging_fee > 8000:

    fee_message = "보통 요금"

    st.info(
        "충전요금 보통"
    )

else:

    fee_message = "낮은 요금"

    st.success(
        "충전요금 낮음"
    )

st.write(
    f"지금은 전기가 {fee_message}인 시간대입니다."
)
if (
        outside_temperature > 30
        and charging_type_text == '급속'
    ):

        st.warning(
            "고온 환경에서 급속충전 시 "
            "배터리 발열 위험이 증가할 수 있습니다."
        )

if load_score == 2:

        st.warning(
            "현재는 최대부하 시간대입니다."
        )

if charging_fee > 15000:

        st.info(
            "현재 시간대는 충전요금이 높은 편입니다."
        )