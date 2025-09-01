from bson import ObjectId
from pymongo import ReturnDocument
from motor.motor_asyncio import AsyncIOMotorCollection
from pydantic import BaseModel
from uuid import uuid4

class ListSummary(BaseModel):
    id: str
    name: str
    item_count: int

    @staticmethod
    def from_doc(doc) -> "ListSummary":
        return ListSummary(
            id=str(doc["_id"]),
            name=doc["name"],
            item_count=doc.get("item_count", 0)
        )
    
    class ToDoListItem(BaseModel):
        id: str
        description: str
        completed: bool

        @staticmethod
        def from_doc(doc) -> "ToDoListItem":
            return ToDoListItem(
                id=item["_id"],
                label=item["label"],
                checked=item["checked"]
            )
        
    class ToDoList(BaseModel):
        id: str
        name: str
        items: list[ToDoListItem]

        @staticmethod
        def from_doc(doc) -> "ToDoList":
            return ToDoList(
                id=str(doc["_id"]),
                name=doc["name"],
                items=[ToDoListItem.from_doc(item) for item in doc.get("items", [])]
            )
        
    class ToDoDAL:
        def __init__(self, collection: AsyncIOMotorCollection):
            self.collection = collection

        async def list_todo_lists(self, session=None):
            async for doc in self.collection.find(
                {},
                projection={
                    "name": 1,
                    "item_count": {"$size": "$items"},
                },
                sorted={"name": 1},
                session=session
            ):  
                yield ListSummary.from_doc(doc)

        async def get_todo_list(self, list_id: str, session=None) -> ToDoList | None:
            doc = await self.collection.find_one(
                {"_id": ObjectId(list_id)},
                session=session
            )
            if doc:
                return ToDoList.from_doc(doc)
            return None
        async def create_todo_list(self, name: str, session=None) -> ToDoList:
            response = await self.collection.insert_one(
                {
                    "name": name,
                    "items": []
                },
                session=session
            )

        async def delete_todo_list(self, list_id: str, session=None) -> bool:
            result = await self.collection.delete_one(
                {"_id": ObjectId(list_id)},
                session=session
            )
            return result.deleted_count == 1
        
        async def createItem(self,
                             id: str | ObjectId,
                             label: str,
                             session=None) -> ToDoList | None:
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(id)},
                {
                    "$push": {
                        "items": {
                            "_id": str(uuid4()),
                            "label": label,
                            "checked": False
                        }
                    }
                },
                return_document=ReturnDocument.AFTER,
                session=session
            )
            if result:
                return ToDoList.from_doc(result)
            
            async def set_checked_state(self,
                                        list_id: str | ObjectId,
                                        item_id: str,
                                        checked: bool,
                                        session=None) -> ToDoList | None:
                result = await self.collection.find_one_and_update(
                    {
                        "_id": ObjectId(list_id),
                        "items._id": item_id
                    },
                    {
                        "$set": {
                            "items.$.checked": checked
                        }
                    },
                    return_document=ReturnDocument.AFTER,
                    session=session
                )
                if result:
                    return ToDoList.from_doc(result)
                return None
        
        async def delete_item(self,
                              list_id: str | ObjectId,
                              item_id: str,
                              session=None) -> ToDoList | None:
            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(list_id)},
                {
                    "$pull": {
                        "items": {
                            "_id": item_id
                        }
                    }   
                },
                return_document=ReturnDocument.AFTER,
                session=session
            )
            if result:
                return ToDoList.from_doc(result)
            return None
            