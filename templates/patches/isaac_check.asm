	jump_if_event_false EVENT_BEAT_JENNIFER, .isaac_check
	jump_if_event_false EVENT_BEAT_NICHOLAS, .isaac_check
	jump_if_event_false EVENT_BEAT_BRANDON, .isaac_check
	script_jump .start_dialogue

.isaac_check
	print_npc_text IsaacCheck
	quit_script_fully
