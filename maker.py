from typing import List
import streamlit as st
import json
import os
import time
from dotenv import load_dotenv
import sys
from pydantic import parse_obj_as, ValidationError
from llm import (
    get_split_record,
    get_gpt_record,
    auto_gpt_record,
    Item,
    ItemAdapter,
)

sys.setrecursionlimit(100000)


def rerun():
    st.rerun()


data_file = os.getenv("DATA_FILE", "")
if not os.path.exists(data_file):
    st.warning(f"{data_file} not found")
    rerun()


index_file = "./data/" + data_file.split(".")[0] + "_index.json"


def save_data():
    st.session_state["filename_index"] = (
        st.session_state["index"] // st.session_state["split_num"]
    )
    filename = f'{st.session_state["filename_prefix"]}_{st.session_state["filename_index"]}.json'
    with open(filename, "w") as f:
        json.dump(st.session_state["data"], f, ensure_ascii=False, indent=4)
        f.close()


def save_index():
    st.session_state["filename_index"] = (
        st.session_state["index"] // st.session_state["split_num"]
    )
    with open(index_file, "w") as f:
        json.dump(
            {
                "index": st.session_state["index"],
                "split_num": st.session_state["split_num"],
                "split_count": st.session_state["split_count"],
                "count": st.session_state["count"],
                "filename_index": st.session_state["filename_index"],
                "filename_prefix": st.session_state["filename_prefix"],
            },
            f,
            ensure_ascii=False,
            indent=4,
        )
        f.close()


def update_index(index):
    st.session_state["index"] = index
    save_index()


def navigate_previous():
    update_index(max(0, st.session_state["index"] - 1))
    st.session_state["navigate"] = navigate_previous


def navigate_next():
    update_index(
        min(
            st.session_state["count"] - 1,
            st.session_state["index"] + 1,
        )
    )
    st.session_state["navigate"] = navigate_next


def read_file(index, filename_prefix):
    filename = f"{filename_prefix}_{index}.json"
    with open(filename, "r") as file:
        data = json.load(file)
        file.close()
    return data


def split_and_write(data, count, filename_prefix):
    num_batches = len(data) // count
    remainder = len(data) % count

    for i in range(num_batches):
        batch_data = data[i * count : (i + 1) * count]
        filename = f"{filename_prefix}_{i}.json"
        if os.path.exists(filename):
            continue
        with open(filename, "w") as file:
            json.dump(
                batch_data,
                file,
                ensure_ascii=False,
                indent=4,
            )
            file.close()

    if remainder > 0:
        batch_data = data[num_batches * count :]
        filename = f"{filename_prefix}_{num_batches}.json"
        if os.path.exists(filename):
            return
        with open(filename, "w") as file:
            json.dump(
                batch_data,
                file,
                ensure_ascii=False,
                indent=4,
            )
            file.close()


def load_data():
    filename_prefix = "./data/" + data_file.split(".")[0]
    split_num = 100

    if not os.path.exists(index_file):

        data = []
        with open(data_file, "r") as f:
            data = json.load(f)
            f.close()
        count = len(data)
        split_count = (count - 1) // split_num + 1

        with open(index_file, "w") as f:
            json.dump(
                {
                    "index": 0,
                    "split_num": split_num,
                    "split_count": split_count,
                    "count": count,
                    "filename_index": 0,
                    "filename_prefix": filename_prefix,
                },
                f,
                ensure_ascii=False,
                indent=4,
            )
            f.close()

        split_and_write(data, split_num, filename_prefix)

    with open(index_file, "r") as f:
        data = json.load(f)
        st.session_state["index"] = data["index"]
        st.session_state["split_num"] = data["split_num"]
        st.session_state["split_count"] = data["split_count"]
        st.session_state["count"] = data["count"]
        st.session_state["filename_index"] = data["filename_index"]
        st.session_state["filename_prefix"] = data["filename_prefix"]
        f.close()

    st.session_state["data"] = read_file(
        st.session_state["filename_index"], st.session_state["filename_prefix"]
    )


def load_item():
    index = st.session_state["index"] % st.session_state["split_num"]
    if index < len(st.session_state["data"]):
        item = st.session_state["data"][index]
    else:
        item = {"instruction": "", "input": "", "output": ""}
    st.session_state["instruction"] = item["instruction"]
    if "input" in item:
        st.session_state["input"] = item["input"]
    st.session_state["output"] = item["output"]
    if "before_instruction" in item:
        st.session_state["before_instruction"] = item["before_instruction"]
    else:
        st.session_state["before_instruction"] = ""
    if "before_output" in item:
        st.session_state["before_output"] = item["before_output"]
    else:
        st.session_state["before_output"] = ""
    if "reason" in item:
        st.session_state["reason"] = item["reason"]
    else:
        st.session_state["reason"] = ""
    if "is_relevant" in item:
        st.session_state["is_relevant"] = item["is_relevant"]
    else:
        st.session_state["is_relevant"] = True
    if "deleted" in item:
        st.session_state["deleted"] = item["deleted"]
    else:
        st.session_state["deleted"] = False


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
    if "navigate" not in st.session_state:
        st.session_state["navigate"] = navigate_next
    if "is_auto_fix" not in st.session_state:
        st.session_state["is_auto_fix"] = False
    if "reason" not in st.session_state:
        st.session_state["reason"] = ""
    if "is_relevant" not in st.session_state:
        st.session_state["is_relevant"] = True
    if "deleted" not in st.session_state:
        st.session_state["deleted"] = False


load_data()
load_item()
initialize_session_state()


def update_sidebar():
    max_value = (st.session_state["count"] - 1) // per_page + 1
    page = st.sidebar.number_input(
        "Page Count : "
        + str(max_value)
        + "\n\n当前进度 : "
        + str(st.session_state["index"] + 1)
        + " / "
        + str(st.session_state["count"])
        + " ("
        + str(
            round((st.session_state["index"] + 1) / st.session_state["count"] * 100, 6)
        )
        + "%)",
        min_value=1,
        max_value=max_value,
        value=int((st.session_state["index"] / per_page + 1)),
    )

    st.session_state["filename_index"] = (
        (page - 1) * per_page // st.session_state["split_num"]
    )

    st.session_state["data"] = read_file(
        st.session_state["filename_index"], st.session_state["filename_prefix"]
    )

    start = int((page - 1) * per_page) % st.session_state["split_num"]
    end = int(
        min(
            len(st.session_state["data"]),
            page * per_page
            - st.session_state["filename_index"] * st.session_state["split_num"],
        )
    )
    for i in range(start, end):
        key = "instruction_" + str(i)
        title = "[" + st.session_state["data"][i]["instruction"] + "]"
        desc = "[" + st.session_state["data"][i]["output"] + "]"
        if (
            "deleted" in st.session_state["data"][i]
            and st.session_state["data"][i]["deleted"]
        ):
            title = ":red" + title
            desc = ":red" + desc
        else:
            title = ":blue" + title
            desc = ":blue" + desc
        if st.sidebar.button(title, key):
            update_index(
                i + st.session_state["filename_index"] * st.session_state["split_num"]
            )
            rerun()
        st.sidebar.caption(desc)


def delete_record():
    if len(st.session_state["data"]) > 0:
        st.session_state["data"].pop(st.session_state["index"])
        save_data()
        update_index(min(len(st.session_state["data"]) - 1, st.session_state["index"]))
        st.success("当前记录已删除")


if st.session_state["reason"] != "":
    reason = "[" + st.session_state["reason"] + "]"
    if "deleted" in st.session_state and st.session_state["deleted"]:
        reason = ":red" + reason
    else:
        reason = ":blue" + reason
    st.caption(reason)

add_num = st.number_input("输入要分裂的数据数量", min_value=1, value=1)
instruction = st.text_area(
    "Instruction", value=st.session_state["instruction"], height=100
)
if st.session_state["before_instruction"] != "":
    st.caption("Before Instruction : " + st.session_state["before_instruction"])
# input_text = st.text_area("Input", value=st.session_state["input"], height=40)
input_text = ""
output = st.text_area("Output", value=st.session_state["output"], height=120)
if st.session_state["before_output"] != "":
    st.caption("Before Output : " + st.session_state["before_output"])


def add_record():
    split_record(query={"instruction": "", "input": "", "output": ""}, num=1)


def save_record(item):
    index = st.session_state["index"] % st.session_state["split_num"]
    if index < len(st.session_state["data"]):
        beforeItem = st.session_state["data"][index]
        if (
            "before_instruction" not in beforeItem
            and item["instruction"] != beforeItem["instruction"]
        ):
            beforeItem["before_instruction"] = beforeItem["instruction"]
        if "before_output" not in beforeItem and item["output"] != beforeItem["output"]:
            beforeItem["before_output"] = beforeItem["output"]

        if (
            "before_instruction" in beforeItem
            and item["instruction"] != beforeItem["before_instruction"]
        ):
            item["before_instruction"] = beforeItem["before_instruction"]

        if (
            "before_output" in beforeItem
            and item["output"] != beforeItem["before_output"]
        ):
            item["before_output"] = beforeItem["before_output"]

        if "reason" in beforeItem:
            item["reason"] = beforeItem["reason"]
        if "is_relevant" in beforeItem:
            item["is_relevant"] = beforeItem["is_relevant"]
        if "deleted" in beforeItem:
            item["deleted"] = beforeItem["deleted"]
        st.session_state["data"][index] = item
    else:
        st.session_state["data"].append(item)
    save_data()
    st.success("数据已保存")


def split_record(query, num=None):
    if num is None:
        queries = get_split_record(query, add_num)
    else:
        queries = [query]

    # 验证 queries
    try:
        queries = ItemAdapter.validate_python(queries)
    except ValidationError as e:
        st.warning(f"Queries validation failed: {e}")
        return

    print(json.dumps(queries, ensure_ascii=False, indent=4))

    queries.reverse()
    for query in queries:
        if len(st.session_state["data"]) <= 0:
            st.session_state["data"].append(query)
        else:
            st.session_state["data"].insert(st.session_state["index"] + 1, query)
    st.success(f"已插入 {len(queries)} 条数据")
    save_data()


def gpt_record(query):
    anser = get_gpt_record(query)
    query["output"] = anser
    save_record(query)


def auto_record(query):
    record = auto_gpt_record(query)
    queries = [record]
    # 验证 queries
    try:
        queries = ItemAdapter.validate_python(queries)
    except ValidationError as e:
        st.warning(f"Queries validation failed: {e}")
        query["is_relevant"] = False
        return query
    return record


per_page = 5
update_sidebar()

cols = st.columns(9)

if cols[0].button("add"):
    add_record()
    rerun()

if cols[1].button("split"):
    with st.spinner("分裂中..."):
        split_record(
            query={"instruction": instruction, "input": input_text, "output": output}
        )
        navigate_next()
        rerun()

if cols[2].button("ask"):
    with st.spinner("思考中..."):
        gpt_record({"instruction": instruction, "input": input_text, "output": output})
        rerun()


def auto_fix():
    with st.spinner("自动纠正中..."):
        if st.session_state["index"] == (st.session_state["count"] - 1):
            st.session_state["is_auto_fix"] = False

        record = auto_record(
            {"instruction": instruction, "input": input_text, "output": output}
        )
        print(time.time())
        print(json.dumps(record, ensure_ascii=False, indent=4))
        if (
            "is_relevant" in record
            and "reason" in record
            and record["is_relevant"] == False
        ):
            st.warning(record["reason"])
            save_record(
                {
                    "instruction": instruction,
                    "input": input_text,
                    "output": output,
                    "deleted": True,
                    "is_relevant": record["is_relevant"],
                    "reason": record["reason"],
                }
            )
            navigate_next()
        elif (
            "reason" in record
            and "instruction" in record
            and "output" in record
            and "is_relevant" in record
        ):
            st.success(record["reason"])
            save_record(
                {
                    "instruction": record["instruction"],
                    "input": input_text,
                    "output": record["output"],
                    "is_relevant": record["is_relevant"],
                    "reason": record["reason"],
                }
            )
            navigate_next()
        rerun()


if cols[3].button("auto"):
    if st.session_state["is_auto_fix"]:
        st.session_state["is_auto_fix"] = False
    else:
        st.session_state["is_auto_fix"] = True
    rerun()

if cols[4].button("del"):
    save_record(
        {
            "instruction": instruction,
            "input": input_text,
            "output": output,
            "deleted": True,
        }
    )
    rerun()


if cols[5].button("save"):
    save_record({"instruction": instruction, "input": input_text, "output": output})
    rerun()

if cols[6].button("pre"):
    save_record({"instruction": instruction, "input": input_text, "output": output})
    navigate_previous()
    rerun()

if cols[7].button("next"):
    save_record({"instruction": instruction, "input": input_text, "output": output})
    navigate_next()
    rerun()


if st.session_state["is_auto_fix"]:
    try:
        auto_fix()
    except Exception as e:
        st.warning(f"auto_fix failed: {e}")
        rerun()
