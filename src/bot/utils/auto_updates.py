# TODO check ability to implement something alike
# async def update_menu_for_all_users(bot: Bot, *ignore_list):
#     curr = None
#     for user_id, message in db.last_message.items():
#         old: str = message.text
#         if old.startswith("🎧"):
#             if curr is None:
#                 try:
#                     curr = await get_menu_text()
#                 except ConnectionError:
#                     await handle_connection_error(message, bot)
#                     return
#             if user_id not in ignore_list:
#                 old_split = old.split('\n\n')
#                 old_split = [item[item.find(":") + 2:] for item in old_split]
#                 curr_split = curr.split('\n\n')
#                 curr_split = [item[item.find(":") + 2:] for item in curr_split]
#                 if old_split != curr_split:
#                     if user_id in db.admins:
#                         markup = get_admin_menu_keyboard()
#                     else:
#                         markup = get_user_menu_keyboard()
#                     try:
#                         msg = await bot.edit_message_text(chat_id=user_id, text=curr, message_id=message.message_id,
#                                                           reply_markup=markup)
#                         # db.update_last_message(user_id, msg)
#                     except:
#                         pass
#
#
# async def update_queue_for_all_users(bot: Bot):
#     queue = None
#     for user_id, message in db.last_message.items():
#         old: str = message.text
#         if old.startswith('треки в очереди') or old.startswith("в очереди нет треков"):
#             if queue is None:
#                 try:
#                     queue = await get_queue_text()
#                 except PremiumRequired:
#                     await handle_connection_error(message, bot)
#                     return
#                 except ConnectionError:
#                     await handle_premium_required_error(message)
#                     return
#             if queue is None:
#                 new = "в очереди нет треков"
#             else:
#                 new = "треки в очереди:\n\n" + queue
#             if old != new:
#                 try:
#                     msg = await bot.edit_message_text(chat_id=user_id, text=new, message_id=message.message_id,
#                                                       reply_markup=get_menu_keyboard())
#                     # db.update_last_message(user_id, msg)
#                 except:
#                     pass
