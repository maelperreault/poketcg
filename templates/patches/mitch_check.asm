    fight_club_pupil_jump .first_interaction, .three_pupils_remaining, \
.two_pupils_remaining, .one_pupil_remaining, .all_pupils_defeated

.first_interaction
	print_npc_text MitchCheck
	set_event EVENT_PUPIL_MICHAEL_STATE, PUPIL_ACTIVE
	set_event EVENT_PUPIL_CHRIS_STATE, PUPIL_ACTIVE
	set_event EVENT_PUPIL_JESSICA_STATE, PUPIL_ACTIVE
	quit_script_fully

.three_pupils_remaining
	print_text_quit_fully Text0478

.two_pupils_remaining
	print_text_quit_fully Text0479

.one_pupil_remaining
	print_text_quit_fully Text047a

.all_pupils_defeated
	print_npc_text Text047b
	script_jump .start_dialogue
