	jump_if_event_true EVENT_KEN_HAD_ENOUGH_CARDS, .have_300_cards
	jump_if_enough_cards_owned 300, .have_300_cards
	print_npc_text KenCheck
	quit_script_fully

.have_300_cards
	max_out_event_value EVENT_KEN_HAD_ENOUGH_CARDS
	script_jump .start_dialogue
