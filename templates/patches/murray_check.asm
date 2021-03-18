	try_give_medal_pc_packs
	jump_if_event_greater_or_equal EVENT_MEDAL_COUNT, 4, .start_dialogue
	print_npc_text MurrayCheck
	quit_script_fully
