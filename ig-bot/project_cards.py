from issues import move_issue, get_proj_id, get_target_column

from util import get_api_data
from static import accept_headers
from settings import get_orgname, get_sprint_name
from settings import get_main_proj, read_project_columns
from projects import get_org_projects, get_project_columns, get_project_cards


async def try_move_card(event_data, headers):
    "attempt to move the issue that was labeled to an appropriate column"
    label_name = event_data.get("label", {}).get("name", None)
    if label_name == "status: in-review":
        await move_to("To do", event_data, headers)
    elif label_name == "status: in-development":
        await move_to("In Progress", event_data, headers)
    elif label_name == "status: resolved":
        await move_to("Done", event_data, headers)


async def move_to(target_col, event_data, headers):
    "move an issue to a specific column"
    org_name = get_orgname()
    cur_sprint = get_sprint_name()
    issue_id = event_data.get("issue").get("id")
    proj_id = await get_proj_id(cur_sprint, org_name, headers)
    cur_col = await get_current_col(proj_id, headers, issue_id)
    if cur_col is None:
        return
    cur_col_data = await get_col_data(cur_col.get("name"), proj_id, cur_sprint, headers)
    tgt_col_data = await get_col_data(target_col, proj_id, cur_sprint, headers)
    issue_card = await get_target_card(cur_col_data, event_data, headers)
    await move_issue(target_col, issue_card, tgt_col_data["col_id"], headers)


async def get_current_col(proj_id, headers, issue_id):
    "get the column where the issue-to-be-moved currently is"
    columns = await get_project_columns(proj_id, headers)
    for col in columns:
        cards_url = col.get("cards_url")
        col_cards = await get_api_data(cards_url, headers)
        for card in col_cards:
            card_issue_url = card.get("content_url")
            if card_issue_url == None:
                continue
            card_issue = await get_api_data(card_issue_url, headers)
            if card_issue.get("id") == issue_id:
                return col


async def get_col_data(col_name, proj_id, cur_sprint, headers):
    "get a column's cards and id"
    tgt_col = await get_target_column(proj_id, cur_sprint, col_name, headers)
    col_id = tgt_col.get("id")
    cards = await get_project_cards(col_id, headers)
    return {"cards": cards, "col_id": col_id}


async def get_target_card(col_data, event_data, headers):
    "get the card that is to be moved"
    cards = col_data["cards"]
    tgt_issue_id = event_data.get("issue").get("id")
    for card in cards:
        card_issue_url = card.get("content_url")
        if card_issue_url == None:
            continue
        card_issue = await get_api_data(card_issue_url, headers)
        if card_issue.get("id") == tgt_issue_id:
            return card
