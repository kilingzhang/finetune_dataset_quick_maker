import json
import os
from dotenv import load_dotenv
from pydantic import TypeAdapter, ValidationError
from typing import Any, List
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI


load_dotenv()

chat = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE_URL"),
    model=os.getenv("OPENAI_API_MODEL", "gpt-3.5-turbo"),
    max_retries=5,
)


# Define your desired data structure.
class Item(BaseModel):
    instruction: str = Field(description="llm训练数据的对话中的用户a输入")
    # input: str = Field(description="llm训练数据的input")
    output: str = Field(description="llm训练数据的对话中的用户b回答")
    reason: str = Field(description="判断依据")
    is_relevant: bool = Field(description="用户a与用户b的对话数据是否存在相关性")


class ItemAdapter(List[Item]):
    @classmethod
    def validate_python(cls, v: Any) -> List[Item]:
        if isinstance(v, list) and (isinstance(i, Item) for i in v):
            return v
        else:
            raise ValidationError("Input is not a list of Item instances", cls)


def get_split_record(query, num):
    del query["input"]
    # And a query intented to prompt a language model to populate the data structure.
    parser = JsonOutputParser(pydantic_object=Item)

    prompt = PromptTemplate(
        template="根据输入的llm训练数据\n{query}\n给出{num}组高质量，通过组合不同的内容语义相同，但说法不同的表达的instruction，和内容语义相同，但说法不同的表达的output。\n{format_instructions}，对象格式如上，返回对象数组。\n",
        input_variables=["query", "num"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | chat | parser

    return chain.invoke({"query": json.dumps(query, ensure_ascii=False), "num": num})


def get_gpt_record(query):
    prompt = PromptTemplate(
        template="{query}",
        input_variables=["query"],
    )
    chain = prompt | chat
    res = chain.invoke({"query": query["instruction"]})
    print(res)
    return res.content


def auto_gpt_record(query):
    del query["input"]
    # And a query intented to prompt a language model to populate the data structure.
    parser = JsonOutputParser(pydantic_object=Item)

    prompt = PromptTemplate(
        template="{query}\n上为llm未标注的用户a与用户b的对话数据。\n首先判断用户输入的'instruction'与'output'内容是否存在关联,如果不存在关联或者无法判断是否存在关联则返回的'instruction','output'数据都要返回空,并且is_relevant为false。如果存在关联，则继续处理数据，is_relevant为true，并且过滤重写输入的'instruction','output'内容中的无用信息，只保留明确有异议的对话信息(如果存在关个人隐私相关的数据，请重写，不可展示真实数据)。注意处理后的'output'数据仅提取回答用户a输入的'instruction'相关内容，如果输入中存在错别字，则帮他修正过来。你的任何思考过程输出到reason中。不许遗漏任何细节，一步一步深思熟虑。\n{format_instructions}",
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chat.temperature = 0.1
    chain = prompt | chat | parser

    return chain.invoke({"query": json.dumps(query, ensure_ascii=False)})
