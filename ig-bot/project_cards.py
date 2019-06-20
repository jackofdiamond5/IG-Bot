import util
import static
import issues
import settings
import projects as proj


async def try_move_card(event_data, headers):
    "attempt to move the issue that was labeled to an appropriate column"
    label_name = event_data.get("label", {}).get("name", None)
    if label_name == static.in_review_lbl:
        await move_to(static.sprint_todo_col, event_data, headers)
    elif label_name == static.in_dev_lbl:
        await move_to(static.in_progress_col, event_data, headers)
    elif label_name == static.resolved_lbl:
        await move_to(static.done_col, event_data, headers)


async def move_to(target_col, event_data, headers):
    "move an issue to a specific column"
    org_name = settings.get_orgname()
    cur_sprint = settings.get_sprint_name()
    issue_id = event_data.get("issue").get("id")
    proj_id = await issues.get_proj_id(cur_sprint, org_name, headers)
    cur_col = await get_current_col(proj_id, headers, issue_id)
    if cur_col is None:
        return
    cur_col_data = await get_col_data(cur_col.get("name"), proj_id, cur_sprint, headers)
    tgt_col_data = await get_col_data(target_col, proj_id, cur_sprint, headers)
    issue_card = await get_target_card(cur_col_data, event_data, headers)
    await issues.move_issue(target_col, issue_card, tgt_col_data["col_id"], headers)


async def get_current_col(proj_id, headers, issue_id):
    "get the column where the issue-to-be-moved currently is"
    columns = await proj.get_project_columns(proj_id, headers)
    for col in columns:
        cards_url = col.get("cards_url")
        col_cards = await util.get_api_data(cards_url, headers)
        for card in col_cards:
            card_issue_url = card.get("content_url")
            if card_issue_url == None:
                continue
            card_issue = await util.get_api_data(card_issue_url, headers)
            if card_issue.get("id") == issue_id:
                return col


async def get_col_data(col_name, proj_id, cur_sprint, headers):
    "get a column's cards and id"
    tgt_col = await issues.get_target_column(proj_id, cur_sprint, col_name, headers)
    col_id = tgt_col.get("id")
    cards = await proj.get_project_cards(col_id, headers)
    return {"cards": cards, "col_id": col_id}


async def get_target_card(col_data, event_data, headers):
    "get the card that is to be moved"
    cards = col_data["cards"]
    tgt_issue_id = event_data.get("issue").get("id")
    for card in cards:
        card_issue_url = card.get("content_url")
        if card_issue_url == None:
            continue
        card_issue = await util.get_api_data(card_issue_url, headers)
        if card_issue.get("id") == tgt_issue_id:
            return card
