from typing import List
import streamlit as st
import json
import os
from pydantic import parse_obj_as, ValidationError
from llm import get_split_record, get_gpt_record, fix_gpt_record, Item, ItemAdapter

index_file = "index.json"
data_file = "self_cognition.json"
data_file = "updated_data.json"


def save_data():
    with open(data_file, "w") as f:
        json.dump(st.session_state["data"], f, ensure_ascii=False, indent=4)


def save_index():
    with open(index_file, "w") as f:
        json.dump({"index": st.session_state["index"]}, f, ensure_ascii=False, indent=4)


def load_data():
    with open(data_file, "r") as f:
        st.session_state["data"] = json.load(f)
    if os.path.exists(index_file):
        with open(index_file, "r") as f:
            data = json.load(f)
            if "index" in data:
                st.session_state["index"] = data["index"]


def load_item():
    index = st.session_state["index"]
    if index < len(st.session_state["data"]):
        item = st.session_state["data"][index]
    else:
        item = {"instruction": "", "input": "", "output": ""}
    st.session_state["instruction"] = item["instruction"]
    st.session_state["input"] = item["input"]
    st.session_state["output"] = item["output"]


def initialize_session_state():
    if "data" not in st.session_state:
        st.session_state["data"] = []
    if "index" not in st.session_state:
        st.session_state["index"] = 0
    if "instruction" not in st.session_state:
        st.session_state["instruction"] = ""
    if "input" not in st.session_state:
        st.session_state["input"] = ""
    if "output" not in st.session_state:
        st.session_state["output"] = ""
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = 1

    if os.path.exists(data_file):
        load_data()
        load_item()


initialize_session_state()


def update_index(index):
    st.session_state["index"] = index
    save_index()
    st.rerun()


def update_sidebar():
    max_value = (len(st.session_state["data"]) - 1) // per_page + 1
    page = st.sidebar.number_input(
        "Page Count : "
        + str(max_value)
        + "\n\n当前进度 : "
        + str(st.session_state["index"] + 1)
        + " / "
        + str(len(st.session_state["data"]))
        + " ("
        + str(round((st.session_state["index"] + 1) / len(st.session_state["data"]), 6))
        + "%)",
        min_value=1,
        max_value=max_value,
        value=1,
    )
    st.sidebar.title("Instructions")
    for i in range(
        int((page - 1) * per_page),
        int(min(len(st.session_state["data"]), page * per_page)),
    ):
        key = "instruction_" + str(i)
        if st.sidebar.button(st.session_state["data"][i]["instruction"], key):
            update_index(i)
        st.sidebar.caption(st.session_state["data"][i]["output"])


def navigate_previous():
    update_index(max(0, st.session_state["index"] - 1))


def navigate_next():
    update_index(min(len(st.session_state["data"]) - 1, st.session_state["index"] + 1))


def delete_record():
    if len(st.session_state["data"]) > 0:
        st.session_state["data"].pop(st.session_state["index"])
        save_data()
        update_index(min(len(st.session_state["data"]) - 1, st.session_state["index"]))
        st.toast("当前记录已删除")
        st.rerun()


add_num = st.number_input("输入要分裂的数据数量", min_value=1, value=1)
instruction = st.text_area(
    "Instruction", value=st.session_state["instruction"], height=100
)
input_text = st.text_area("Input", value=st.session_state["input"], height=40)
output = st.text_area("Output", value=st.session_state["output"], height=120)


def add_record():
    split_record(query={"instruction": "", "input": "", "output": ""}, num=1)


def save_record(item):
    if st.session_state["index"] < len(st.session_state["data"]):
        st.session_state["data"][st.session_state["index"]] = item
    else:
        st.session_state["data"].append(item)
    save_data()
    st.toast("数据已保存")
    st.rerun()


def split_record(query, num=None):
    if num is None:
        queries = get_split_record(query, add_num)
    else:
        queries = [query]

    # 验证 queries
    try:
        queries = ItemAdapter.validate_python(queries)
    except ValidationError as e:
        st.toast(f"Queries validation failed: {e}")
        st.rerun()

    print(json.dumps(queries, ensure_ascii=False, indent=4))

    queries.reverse()
    for query in queries:
        if len(st.session_state["data"]) <= 0:
            st.session_state["data"].append(query)
        else:
            st.session_state["data"].insert(st.session_state["index"] + 1, query)
    st.toast(f"已插入 {len(queries)} 条数据")
    save_data()
    navigate_next()
    st.rerun()


def gpt_record(query):
    anser = get_gpt_record(query)
    query["output"] = anser
    save_record(query)


def fix_record(query):
    query = fix_gpt_record(query)
    print(query)
    queries = [query]
    # 验证 queries
    try:
        queries = ItemAdapter.validate_python(queries)
    except ValidationError as e:
        st.toast(f"Queries validation failed: {e}")
        st.rerun()
    save_record(query)


per_page = 100
update_sidebar()

cols = st.columns(8)

if cols[0].button("新增"):
    add_record()

if cols[1].button("分裂"):
    with st.spinner("分裂中..."):
        split_record(
            query={"instruction": instruction, "input": input_text, "output": output}
        )

if cols[2].button("回答"):
    with st.spinner("思考中..."):
        gpt_record({"instruction": instruction, "input": input_text, "output": output})

if cols[3].button("纠正"):
    with st.spinner("纠正中..."):
        fix_record({"instruction": instruction, "input": input_text, "output": output})


if cols[4].button("删除"):
    delete_record()


if cols[5].button("保存"):
    save_record({"instruction": instruction, "input": input_text, "output": output})

if cols[6].button("上一个"):
    navigate_previous()

if cols[7].button("下一个"):
    navigate_next()
