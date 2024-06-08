/* Python suffix tree */

/* Originally developed by Thomas Mailund <mailund@birc.dk> and S�ren Besenbacher <besen@birc.dk> */
/* Adapted by Dell Zhang <dell.z@ieee.org> to support Unicode text and new verision Python. */

#include <wchar.h>
#include "suffix_tree.h"
#include <Python.h>
#include <structmember.h>


typedef	struct SuffixTreeObject	{
	PyObject_HEAD
	suffix_tree_t *tree;
} SuffixTreeObject;

typedef	struct NodeObject {
	PyObject_HEAD

	/* Add dictionary to handle	user-annotation	*/
	PyObject *dict;

	SuffixTreeObject *tree;
	node_t *node;
} NodeObject;

static PyObject	*SuffixTree_new			(PyTypeObject			   *type,
										 PyObject				   *args,
										 PyObject				   *kwds);
static int		 SuffixTree_init		(SuffixTreeObject		   *self,
										 PyObject				   *args,
										 PyObject				   *kwds);
static PyObject	*SuffixTree_root		(SuffixTreeObject		   *self);
static PyObject	*SuffixTree_string		(SuffixTreeObject		   *self);


static PyObject* wrap_node				(SuffixTreeObject		   *tree,
										 node_t					   *n);


static PyObject	*Node_new				(PyTypeObject			   *type,
										 PyObject				   *args,
										 PyObject				   *kwds);
static void		 Node_dealloc			(NodeObject				   *self);

static int		 Node_compare			(NodeObject				   *n1,
										 NodeObject				   *n2);
static long		 Node_hash				(NodeObject				   *self);

static PyObject	*Node_start				(NodeObject				   *self);
static PyObject	*Node_end				(NodeObject				   *self);
static PyObject	*Node_index				(NodeObject				   *self);
static PyObject	*Node_string_depth		(NodeObject				   *self);

static PyObject	*Node_edge_label		(NodeObject				   *self);
static PyObject	*Node_path_label		(NodeObject				   *self);
static PyObject	*Node_suffix			(NodeObject				   *self);

static PyObject	*Node_parent			(NodeObject				   *self);
static PyObject	*Node_next				(NodeObject				   *self);
static PyObject	*Node_prev				(NodeObject				   *self);
static PyObject	*Node_first_child		(NodeObject				   *self);
static PyObject	*Node_last_child		(NodeObject				   *self);

static PyObject	*Node_is_leaf			(NodeObject				   *self);


/**********************************************************************/
/* exporting stuff to python */
/**********************************************************************/

// static PyGetSetDef SuffixTree_getseters[] =	{
// 	{"root", (getter)SuffixTree_root, NULL,
// 	 "The root-node	of the tree.", 
// 	 NULL /* no	closure	*/
// 	},
// 	{"string", (getter)SuffixTree_string, NULL,
// 	 "The string the tree is built over	+ the terminal symbol.",
// 	 NULL /* no	closure	*/
// 	},

// 	{0}	/* sentinel	*/
// };

// static PyTypeObject SuffixTreeType = {
//     PyVarObject_HEAD_INIT(NULL, 0)
//     "_suffix_tree.SuffixTree", /*tp_name*/
//     sizeof(SuffixTreeObject),  /*tp_basicsize*/
//     0,                         /*tp_itemsize*/
//     0,                         /*tp_dealloc*/
//     0,                         /*tp_print*/
//     0,                         /*tp_getattr*/
//     0,                         /*tp_setattr*/
//     0,                         /*tp_compare*/
//     0,                         /*tp_repr*/
//     0,                         /*tp_as_number*/
//     0,                         /*tp_as_sequence*/
//     0,                         /*tp_as_mapping*/
//     0,                         /*tp_hash */
//     0,                         /*tp_call*/
//     0,                         /*tp_str*/
//     0,                         /*tp_getattro*/
//     0,                         /*tp_setattro*/
//     0,                         /*tp_as_buffer*/
//     Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,  /*tp_flags*/
//     "Suffix tree object",      /* tp_doc */
//     0,                         /* tp_traverse */
//     0,                         /* tp_clear */
//     0,                         /* tp_richcompare */ //to
//     0,                         /* tp_weaklistoffset */
//     0,                         /* tp_iter */
//     0,                         /* tp_iternext */
//     0,                         /* tp_methods */
//     0,                         /* tp_members */
//     SuffixTree_getseters,      /* tp_getset */
//     0,                         /* tp_base */
//     0,                         /* tp_dict */
//     0,                         /* tp_descr_get */
//     0,                         /* tp_descr_set */
//     0,                         /* tp_dictoffset */
//     (initproc)SuffixTree_init, /* tp_init */
//     0,                         /* tp_alloc */
//     SuffixTree_new,            /* tp_new */
// };

static PyGetSetDef SuffixTree_getseters[] = {
    {"root", (getter)SuffixTree_root, NULL,
     "The root-node of the tree.",
     NULL /* no closure */
    },
    {"string", (getter)SuffixTree_string, NULL,
     "The string the tree is built over + the terminal symbol.",
     NULL /* no closure */
    },
    {NULL} /* Sentinel */
};

static PyTypeObject SuffixTreeType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "_suffix_tree.SuffixTree",
    .tp_basicsize = sizeof(SuffixTreeObject),
    .tp_itemsize = 0,
    .tp_dealloc = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_doc = "Suffix tree object",
    .tp_traverse = 0,
    .tp_clear = 0,
    .tp_richcompare = 0,
    .tp_weaklistoffset = 0,
    .tp_iter = 0,
    .tp_iternext = 0,
    .tp_methods = 0,
    .tp_members = 0,
    .tp_getset = SuffixTree_getseters,
    .tp_base = 0,
    .tp_dict = 0,
    .tp_descr_get = 0,
    .tp_descr_set = 0,
    .tp_dictoffset = 0,
    .tp_init = (initproc)SuffixTree_init,
    .tp_alloc = 0,
    .tp_new = SuffixTree_new,
    .tp_hash = 0,
    .tp_call = 0,
    .tp_str = 0,
    .tp_getattro = 0,
    .tp_setattro = 0,
    .tp_as_buffer = 0
};



static PyGetSetDef Node_getseters[]	= {
	{"start", (getter)Node_start, NULL,
	 "The start	index of the label on the edge from	parent to this node.",
	 NULL /* no	closure	*/
	},
	{"end",	(getter)Node_end, NULL,
	 "The end index	of the label on	the	edge from parent to	this node.",
	 NULL /* no	closure	*/
	},
	{"index", (getter)Node_index, NULL,
	 "If the node is a leaf, this is the start of the suffix.  If the node "
	 "is an	inner node,	it is the index	of one of its leaves.",
	 NULL /* no	closure	*/
	},
	{"stringDepth",	(getter)Node_string_depth, NULL,
	 "The string depth (length of the path label) of this node.	"
	 "Notice that this is not the *tree* depth,	that is, not the number	of "
	 "nodes	between	the	root and this node,",
	 NULL /* no	closure	*/
	},

	{"edgeLabel", (getter)Node_edge_label, NULL,
	 "The label	on the edge	to this	node's parent (string[start:end+1]).",
	 NULL /* no	closure	*/
	},
	{"pathLabel", (getter)Node_path_label, NULL,
	 "The label	on the path	to this	node from the root.",
	 NULL /* no	closure	*/
	},
	{"suffix", (getter)Node_suffix,	NULL,
	 "The string string[index:], which for leaves is the correct suffix	"
	 "but for inner	nodes is really	just some suffix.",
	 NULL /* no	closure	*/
	},


	{"parent", (getter)Node_parent,	NULL,
	 "The parent of	this node, or None if the node is the root.",
	 NULL /* no	closure	*/
	},
	{"next", (getter)Node_next,	NULL,
	 "The next sibling of this node, or	None.",
	 NULL /* no	closure	*/
	},
	{"prev", (getter)Node_prev,	NULL,
	 "The previous sibling of this node, or	None.",
	 NULL /* no	closure	*/
	},
	{"firstChild", (getter)Node_first_child, NULL,
	 "The first	child of this node,	or None.",
	 NULL /* no	closure	*/
	},
	{"lastChild", (getter)Node_last_child, NULL,
	 "The last child of	this node, or None.",
	 NULL /* no	closure	*/
	},

	{ "isLeaf",	(getter)Node_is_leaf, NULL,
	  "Predicate that is true if self is a leaf, false otherwise.",	NULL
	},

	{0}	/* sentinel	*/
};

// static PyTypeObject	NodeType = {
// 	PyObject_HEAD_INIT(NULL)
// 	0,						   /*ob_size*/
// 	"_suffix_tree.SuffixTreeNode", /*tp_name*/
// 	sizeof(NodeObject),		   /*tp_basicsize*/
// 	0,						   /*tp_itemsize*/
// 	(destructor)Node_dealloc,  /*tp_dealloc*/
// 	0,						   /*tp_print*/
// 	0,						   /*tp_getattr*/
// 	0,						   /*tp_setattr*/
// 	(cmpfunc)Node_compare,	   /*tp_compare*/
// 	0,						   /*tp_repr*/
// 	0,						   /*tp_as_number*/
// 	0,						   /*tp_as_sequence*/
// 	0,						   /*tp_as_mapping*/
// 	(hashfunc)Node_hash,	   /*tp_hash */
// 	0,						   /*tp_call*/
// 	0,						   /*tp_str*/
// 	0,						   /*tp_getattro*/
// 	0,						   /*tp_setattro*/
// 	0,						   /*tp_as_buffer*/
// 	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,  /*tp_flags*/
// 	"Suffix	tree node object", /* tp_doc */
// 	0,						   /* tp_traverse */
// 	0,						   /* tp_clear */
// 	0,						   /* tp_richcompare */
// 	0,						   /* tp_weaklistoffset	*/
// 	0,						   /* tp_iter */
// 	0,						   /* tp_iternext */
// 	0,						   /* tp_methods */
// 	0,						   /* tp_members */
// 	Node_getseters,			   /* tp_getset	*/
// 	0,						   /* tp_base */
// 	0,						   /* tp_dict */
// 	0,						   /* tp_descr_get */
// 	0,						   /* tp_descr_set */
// 	offsetof(NodeObject,dict), /* tp_dictoffset	*/
// 	0,						   /* tp_init */
// 	0,						   /* tp_alloc */
// 	Node_new,				   /* tp_new */
// };

// static PyTypeObject NodeType = {
//     PyVarObject_HEAD_INIT(NULL, 0)
//     "_suffix_tree.SuffixTreeNode", /* tp_name */
//     sizeof(NodeObject),            /* tp_basicsize */
//     0,                             /* tp_itemsize */
//     (destructor)Node_dealloc,      /* tp_dealloc */
//     0,                             /* tp_print */
//     0,                             /* tp_getattr */
//     0,                             /* tp_setattr */
//     0,                             /* tp_reserved */
//     0,                             /* tp_repr */
//     0,                             /* tp_as_number */
//     0,                             /* tp_as_sequence */
//     0,                             /* tp_as_mapping */
//     (hashfunc)Node_hash,           /* tp_hash */
//     0,                             /* tp_call */
//     0,                             /* tp_str */
//     0,                             /* tp_getattro */
//     0,                             /* tp_setattro */
//     0,                             /* tp_as_buffer */
//     Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /* tp_flags */
//     "Suffix tree node object",     /* tp_doc */
//     0,                             /* tp_traverse */
//     0,                             /* tp_clear */
//     0,                             /* tp_richcompare */
//     0,                             /* tp_weaklistoffset */
//     0,                             /* tp_iter */
//     0,                             /* tp_iternext */
//     0,                             /* tp_methods */
//     0,                             /* tp_members */
//     0,                             /* tp_getset */
//     0,                             /* tp_base */
//     0,                             /* tp_dict */
//     0,                             /* tp_descr_get */
//     0,                             /* tp_descr_set */
//     offsetof(NodeObject, dict),    /* tp_dictoffset */
//     0,                             /* tp_init */
//     0,                             /* tp_alloc */
//     Node_new,                      /* tp_new */
// };
static PyTypeObject NodeType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "_suffix_tree.SuffixTreeNode",
    .tp_basicsize = sizeof(NodeObject),
    .tp_dealloc = (destructor)Node_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_doc = "Suffix tree node object",
    .tp_getset = Node_getseters,
    .tp_new = Node_new,
    .tp_hash = (hashfunc)Node_hash,
    .tp_richcompare = 0,
    .tp_iter = 0,
    .tp_methods = 0,
    .tp_members = 0,
    .tp_init = 0,
    .tp_alloc = 0,
    .tp_as_number = 0,
    .tp_as_sequence = 0,
    .tp_as_mapping = 0,
    .tp_call = 0,
    .tp_str = 0,
    .tp_getattro = 0,
    .tp_setattro = 0,
    .tp_as_buffer = 0,
    .tp_weaklistoffset = 0,
    .tp_iter = 0,
    .tp_iternext = 0,
    .tp_descr_get = 0,
    .tp_descr_set = 0,
    .tp_dictoffset = offsetof(NodeObject, dict),
    .tp_clear = 0,
    .tp_traverse = 0
};

static PyMethodDef _suffix_tree_methods[] =	{
	{NULL}	/* Sentinel	*/
};

// #ifndef	PyMODINIT_FUNC	/* declarations	for	DLL	import/export */
// #define	PyMODINIT_FUNC void
// #endif
// PyMODINIT_FUNC
// init_suffix_tree(void) 
// {
// 	PyObject *m;

// 	if (PyType_Ready(&SuffixTreeType) <	0) 
// 		return;
// 	if (PyType_Ready(&NodeType)	< 0) 
// 		return;

// 	m =	Py_InitModule3("_suffix_tree", _suffix_tree_methods,
// 					   "Wrapper module for suffix trees.");

//     if (m == NULL)
// 		return;

// 	Py_INCREF(&SuffixTreeType);
// 	Py_INCREF(&NodeType);

// 	PyModule_AddObject(m, "SuffixTree",	(PyObject *)&SuffixTreeType);
// }

#ifndef PyMODINIT_FUNC
#define PyMODINIT_FUNC PyObject*
#endif

static struct PyModuleDef _suffix_tree_module = {
    PyModuleDef_HEAD_INIT,
    "_suffix_tree",
    "Wrapper module for suffix trees.",
    -1,
    _suffix_tree_methods
};


PyMODINIT_FUNC PyInit__suffix_tree(void) 
{
    PyObject *m;

    if (PyType_Ready(&SuffixTreeType) < 0)
        return NULL;
    if (PyType_Ready(&NodeType) < 0)
        return NULL;

    m = PyModule_Create(&_suffix_tree_module);
    if (m == NULL)
        return NULL;

    Py_INCREF(&SuffixTreeType);
    Py_INCREF(&NodeType);

    PyModule_AddObject(m, "SuffixTree", (PyObject *)&SuffixTreeType);
    PyModule_AddObject(m, "SuffixTreeNode", (PyObject *)&NodeType);

    return m;
}


/**********************************************************************/
/* tree	bindings */
/**********************************************************************/


static PyObject	*
SuffixTree_new(PyTypeObject	*type, PyObject	*args, PyObject	*kwds)
{
	SuffixTreeObject *self = (SuffixTreeObject *)type->tp_alloc(type, 0);
	self->tree = NULL;
	return (PyObject*)self;
}

static int
SuffixTree_init(SuffixTreeObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *string = NULL;
    PyObject *terminal = NULL;
    static char *kwlist[] = {"string", "terminal", NULL};

    wchar_t *s;
    wchar_t t[1];
    int n;
    Py_ssize_t input_string_size;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|UO", kwlist, &string, &terminal))
        return -1;

    if (!(string = PyTuple_GetItem(args, 0))) return -1;
    if (!(terminal = PyTuple_GetItem(args, 1))) return -1;

    input_string_size = PyUnicode_GetLength(string);
    s = malloc((input_string_size + 1) * sizeof(wchar_t));
    if ((n = PyUnicode_AsWideChar(string, s, input_string_size)) < 0) return -1;
    if ((n = PyUnicode_AsWideChar(terminal, t, 1)) < 0) return -1;

    if (n != 1) {
        PyErr_SetString(PyExc_RuntimeError, "Terminal symbol must be a single character!");
        free(s);
        return -1;
    }

    s[input_string_size] = '\0';
    t[0] = '\0';

    self->tree = st_make(s, *t);
    free(s);

    if (!self->tree) {
        PyErr_SetString(PyExc_MemoryError, "Could not allocate suffix tree!");
        return -1;
    }

    return 0;
}
static PyObject	*
SuffixTree_string(SuffixTreeObject *self)
{
	return PyUnicode_FromWideChar(self->tree->str, self->tree->str_len);
}


static PyObject* 
wrap_node(SuffixTreeObject *tree, node_t *n)
{
	NodeObject *node;
	if (n->python_node)
	{
		Py_INCREF((PyObject*)n->python_node);
		return (PyObject*)n->python_node;
	}

	node = (NodeObject*)_PyObject_New((PyTypeObject*)&NodeType);
	if (!node) return 0;

	node->dict = PyDict_New();
	node->tree = tree;
	node->node = n;

	//Py_INCREF((PyObject*)tree); //FIXME: handle cyclic GC	and	make
	//sure tree	isn't deleted while	we have	a node

	// make	sure the node is never deleted while the tree is in	existence
	Py_INCREF(node);
	n->python_node = node;

	return (PyObject*)node;
}

static PyObject*
SuffixTree_root(SuffixTreeObject *self)
{
	return wrap_node(self,self->tree->root);
}




/**********************************************************************/
/* node	bindings */
/**********************************************************************/

static PyObject	*
Node_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
	NodeObject *self = (NodeObject *)type->tp_alloc(type, 0);
	self->dict = NULL;
	self->tree = NULL;
	self->node = NULL;
	return (PyObject*)self;
}

static int
Node_clear(NodeObject *self)
{
	Py_XDECREF(self->dict);	self->dict = NULL;
	Py_XDECREF(self->tree);	self->tree = NULL;
	return 0;
}

static void
Node_dealloc(NodeObject *self)
{
    Node_clear(self);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static int
Node_compare(NodeObject	*n1, NodeObject	*n2)
{
	return (int)(n1->node -	n2->node);
}

static long
Node_hash(NodeObject *self)
{
	return (long)(self->node);
}



static PyObject *
Node_start(NodeObject *self)
{
    return PyLong_FromLong(self->node->start);
}
static PyObject *
Node_end(NodeObject *self)
{
    return PyLong_FromLong(self->node->end);
}


static PyObject	*
Node_index(NodeObject *self)
{
	return PyLong_FromLong(self->node->term_number);
}

static PyObject	*
Node_string_depth(NodeObject *self)
{
	return PyLong_FromLong(self->node->depth);
}


static PyObject	*
Node_edge_label(NodeObject *self)
{
	int	start =	self->node->start;
	int	end	= self->node->end+1;
	int	length = end-start;

	/* the root	is a special case... */
	if (start <	0) return PyUnicode_FromWideChar(L"", 0);
	return PyUnicode_FromWideChar(self->tree->tree->str	+ start, length);
}

static PyObject	*
Node_path_label(NodeObject *self)
{
	int	start =	self->node->term_number;
	int	length = self->node->depth;

	return PyUnicode_FromWideChar(self->tree->tree->str	+ start, length);
}

static PyObject	*
Node_suffix(NodeObject *self)
{
	int	start =	self->node->term_number;
	int	length = self->tree->tree->str_len - start;
	/* the root	is a special case... */
	if (start <	0) return SuffixTree_string(self->tree);
	return PyUnicode_FromWideChar(self->tree->tree->str	+ start, length);
}




static PyObject	*
Node_parent(NodeObject *self)
{
	node_t *parent = self->node->parent;
	if (!parent)
	{
		Py_INCREF(Py_None);
		return Py_None;
	}
	else
	{
		return wrap_node(self->tree,parent);
	}
}

static PyObject	*
Node_next(NodeObject *self)
{
	node_t *next = self->node->next;
	if (!next)
	{
		Py_INCREF(Py_None);
		return Py_None;
	}
	else
	{
		return wrap_node(self->tree,next);
	}
}

static PyObject	*
Node_prev(NodeObject *self)
{
	node_t *prev = self->node->prev;
	if (!prev)
	{
		Py_INCREF(Py_None);
		return Py_None;
	}
	else
	{
		return wrap_node(self->tree,prev);
	}
}

static PyObject	*
Node_first_child(NodeObject	*self)
{
	node_t *c =	self->node->children.head;
	if (!c)
	{
		Py_INCREF(Py_None);
		return Py_None;
	}
	else
	{
		return wrap_node(self->tree,c);
	}
}

static PyObject	*
Node_last_child(NodeObject *self)
{
	node_t *c =	self->node->children.tail;
	if (!c)
	{
		Py_INCREF(Py_None);
		return Py_None;
	}
	else
	{
		return wrap_node(self->tree,c);
	}
}

static PyObject*
Node_is_leaf(NodeObject	*self)
{
	if (self->node && self->node->children.head)
	{ Py_INCREF(Py_False); return Py_False;	}
	else
	{ Py_INCREF(Py_True); return Py_True; }
}
