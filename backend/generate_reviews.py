import asyncio
import random
from datetime import datetime, timedelta
from database import engine, AsyncSessionLocal
from db_models import Base, ReviewModel, ReviewAnalysisModel

# Pre-defined review texts for each category
NORMAL_REVIEWS = [
    "Quality is good", "Fast delivery", "Works as expected",
    "Very satisfied with this purchase", "Decent product for the price",
    "Arrived on time and in perfect condition", "Would buy again",
    "Exactly as described", "No complaints", "Solid build quality",
    "Good product overall. The build quality is decent for the price. Delivery took about 4 days which was reasonable. Would probably buy again."
]

FAKE_REVIEWS = [
    "Great product!!! buy now!!!", "Best ever!!!!", "AMAZING INCREDIBLE FANTASTIC 5 STARS!!!!",
    "HIGHLY RECOMMEND BUY NOW!!!!", "This changed my life forever!!!",
    "WOW WOW WOW!!! Best product EVER!!!!", "Unbelievable quality buy this immediately!!!",
    "Nothing else compares to this amazing item!!!",
    "So incredibly good I bought 10 of them!!!!"
]

SPAM_REVIEWS = [
    "Cheap cheap cheap", "Good good good good", "Nice nice nice",
    "Ok ok ok ok ok", "Very very very very very good",
    "Click my link to get 50% off", "Earn $500 a day from home!!!",
    "Free gift card limited time only", "Best best best best best",
    "Check out my profile for discounts"
]

BOT_REVIEWS = [
    "Best product best product best product.", "Amazing deal amazing deal amazing deal.",
    "Buy this product buy this product now!", "Good quality good quality good quality.",
    "Fast shipping fast shipping fast shipping.", "Very nice very nice very nice.",
    "Loved it loved it loved it.", "Five stars five stars five stars.",
    "Great seller great seller great seller.", "Awesome item awesome item awesome item."
]

async def reset_tables():
    async with engine.begin() as conn:
        print("Dropping review tables...")
        await conn.run_sync(ReviewAnalysisModel.__table__.drop, checkfirst=True)
        await conn.run_sync(ReviewModel.__table__.drop, checkfirst=True)
        
        print("Creating review tables...")
        await conn.run_sync(ReviewModel.__table__.create)
        await conn.run_sync(ReviewAnalysisModel.__table__.create)

async def generate_dataset():
    total_reviews = 2000
    reviews = []
    
    for i in range(1, total_reviews + 1):
        user_id = f"USR_{(i * 137 % 500) + 1000}"
        product_id = f"PRD_{(i * 241 % 200) + 1000}"
        
        rand = random.random()
        rating = 5
        
        if rand < 0.6:
            text = random.choice(NORMAL_REVIEWS)
            rating = random.randint(3, 5)
        elif rand < 0.8:
            text = random.choice(FAKE_REVIEWS)
            rating = 5
        elif rand < 0.9:
            text = random.choice(SPAM_REVIEWS)
            rating = random.randint(4, 5)
        else:
            text = random.choice(BOT_REVIEWS)
            rating = random.randint(1, 4)
            
        days_ago = random.randint(0, 30)
        hours_ago = random.randint(0, 23)
        created_at = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago)
        
        reviews.append(ReviewModel(
            user_id=user_id,
            product_id=product_id,
            review_text=text,
            rating=rating,
            created_at=created_at
        ))
        
    async with AsyncSessionLocal() as session:
        print(f"Inserting {total_reviews} reviews into DB...")
        session.add_all(reviews)
        await session.commit()
        print("Done!")

async def main():
    await reset_tables()
    await generate_dataset()

if __name__ == "__main__":
    asyncio.run(main())
