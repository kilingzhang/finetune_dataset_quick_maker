import json
from pydantic import TypeAdapter, ValidationError
from typing import Any, List
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI

chat = ChatOpenAI(
    api_key="",
    base_url="",
    model="gpt-4",
)


# Define your desired data structure.
class Item(BaseModel):
    instruction: str = Field(description="llm训练数据的instruction")
    input: str = Field(description="llm训练数据的input")
    output: str = Field(description="llm训练数据的output")


class ItemAdapter(List[Item]):
    @classmethod
    def validate_python(cls, v: Any) -> List[Item]:
        if isinstance(v, list) and (isinstance(i, Item) for i in v):
            return v
        else:
            raise ValidationError("Input is not a list of Item instances", cls)


def get_split_record(query, num):
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


def fix_gpt_record(query):
    # And a query intented to prompt a language model to populate the data structure.
    parser = JsonOutputParser(pydantic_object=Item)

    prompt = PromptTemplate(
        template="根据输入的llm未标注的训练数据，排除对话中的无用信息，只保留明确有异议的对话信息(如果存在关个人隐私相关的数据，请重写，不可展示真实数据)。\n{query}\n。\n{format_instructions}。\n",
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    chain = prompt | chat | parser

    return chain.invoke({"query": json.dumps(query, ensure_ascii=False)})
