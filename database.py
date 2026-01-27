import motor.motor_asyncio
import os

# আপনার দেওয়া MongoDB URL সরাসরি এখানে যুক্ত করা হয়েছে
MONGO_URL = "mongodb+srv://SGBACKUP:SGBACKUP@cluster0.64jkmog.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

class Database:
    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.col = self.db.users

    def new_user(self, id):
        """নতুন ইউজারের জন্য একটি ডিকশনারি তৈরি করে"""
        return dict(id=int(id))

    async def add_user(self, id):
        """ইউজারকে ডাটাবেসে সেভ করে যদি সে আগে থেকে না থাকে"""
        user = self.new_user(id)
        if not await self.is_user_exist(id):
            await self.col.insert_one(user)

    async def is_user_exist(self, id):
        """ইউজার ডাটাবেসে আছে কি না চেক করে"""
        user = await self.col.find_one({'id': int(id)})
        return True if user else False

    async def total_users_count(self):
        """মোট ইউজারের সংখ্যা কত তা বের করে"""
        count = await self.col.count_documents({})
        return count

    async def get_all_users(self):
        """ব্রডকাস্ট করার জন্য সমস্ত ইউজারের লিস্ট দেয়"""
        all_users = self.col.find({})
        return all_users

    async def delete_user(self, user_id):
        """ইউজার যদি বট ব্লক করে দেয় তবে তাকে ডাটাবেস থেকে মুছে ফেলে"""
        await self.col.delete_one({'id': int(user_id)})

# ডাটাবেস অবজেক্ট তৈরি করা হচ্ছে যাতে অন্য ফাইলে এটি সরাসরি ব্যবহার করা যায়
db = Database(MONGO_URL, "AutoCaptionBot")
