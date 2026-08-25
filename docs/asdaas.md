refactor: make the category tree explicit in Budget

Add a _children index (parent name -> list of child names) next to the
flat category dict. A parent's children can now be looked up directly
instead of scanning every category, and get_child_total_planned walks
only the children it needs.

add_category rejects a parent that is itself a child: the tree stays two
levels deep, which is what every calculation already assumes. It also
checks that the parent exists before checking depth, so an unknown
parent raises the usual "must be created" error instead of a KeyError.

A child now inherits its parent's is_shared instead of defaulting to
shared. CategoryLibrary.create_category takes the flag so the caller can
pass it down, which also lets a root be created with a flag that differs
from the catalogue default.

set_standard_categories goes through add_category instead of writing to
the dict directly, and skips the categories that already exist. It used
to reset their planned amounts to zero while leaving their children in
place.refactor: make the category tree explicit in Budget

Add a _children index (parent name -> list of child names) next to the
flat category dict. A parent's children can now be looked up directly
instead of scanning every category, and get_child_total_planned walks
only the children it needs.

add_category rejects a parent that is itself a child: the tree stays two
levels deep, which is what every calculation already assumes. It also
checks that the parent exists before checking depth, so an unknown
parent raises the usual "must be created" error instead of a KeyError.

A child now inherits its parent's is_shared instead of defaulting to
shared. CategoryLibrary.create_category takes the flag so the caller can
pass it down, which also lets a root be created with a flag that differs
from the catalogue default.

set_standard_categories goes through add_category instead of writing to
the dict directly, and skips the categories that already exist. It used
to reset their planned amounts to zero while leaving their children in
place.