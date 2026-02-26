
import asyncio
from sqlalchemy import select
from database.session import AsyncSessionFactory, AnalyticsRecord, PredictionLog

async def check_db():
    async with AsyncSessionFactory() as session:
        # Check AnalyticsRecord
        res = await session.execute(select(AnalyticsRecord).order_by(AnalyticsRecord.timestamp.desc()).limit(5))
        records = res.scalars().all()
        print(f"--- Latest AnalyticsRecords ({len(records)}) ---")
        for r in records:
            print(f"ID: {r.id}, TS: {r.timestamp}, AQI: {r.aqi}, Risk: {r.risk_score}")

        # Check PredictionLog
        res = await session.execute(select(PredictionLog).order_by(PredictionLog.id.desc()).limit(5))
        p_logs = res.scalars().all()
        print(f"\n--- Latest PredictionLogs ({len(p_logs)}) ---")
        for p in p_logs:
            print(f"ID: {p.id}, TS: {p.timestamp}, Actual: {p.actual_aqi}, Predicted: {p.predicted_aqi}")

if __name__ == "__main__":
    asyncio.run(check_db())
