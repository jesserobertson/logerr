# Functional Programming Examples

This page walks through a few classic functional-programming algorithms
implemented in `logerr`'s style, to show `Option`/`Result`/`match`-`case`/
`logerr.itertools` working together on something more substantial than a
config-loading pipeline.

## Quicksort

The sorting logic itself can't fail, so plain quicksort doesn't need
`Option`/`Result` at all - it's the textbook recursive partition-and-recurse
definition:

```python
def quicksort[T](items: list[T]) -> list[T]:
    """Classic functional quicksort: partition around a pivot, recurse."""
    if not items:
        return []
    pivot, *rest = items
    smaller = [x for x in rest if x < pivot]
    larger = [x for x in rest if x >= pivot]
    return quicksort(smaller) + [pivot] + quicksort(larger)
```

A more realistic version validates its input first - `Result.traverse`
checks every element and short-circuits on the first one that fails,
then `.map()` chains the pure sort onto the validated list:

```python
from logerr import Ok, Err, Result

def safe_quicksort(raw: list[object]) -> Result[list[int], str]:
    """Validate every element is an int, then quicksort.

    Result.traverse short-circuits on the first non-int - quicksort is
    never called on invalid input.
    """
    return Result.traverse(
        raw,
        lambda x: Ok(x) if isinstance(x, int) else Err(f"Not an int: {x!r}"),
    ).map(quicksort)

safe_quicksort([3, 1, 4, 1, 5])        # Ok([1, 1, 3, 4, 5])
safe_quicksort([3, 1, "oops", 5])      # Err("Not an int: 'oops'")
```

## A Binary Search Tree, `Option`-shaped

A BST node's children are either present or absent - exactly what `Option`
models. Insertion can fail (duplicate key), which is exactly what `Result`
models:

```python
from dataclasses import dataclass
from logerr import Option, Some, Nothing, Result, Ok, Err

@dataclass
class Node[T]:
    value: T
    left: "Option[Node[T]]"
    right: "Option[Node[T]]"

def leaf[T](value: T) -> Node[T]:
    return Node(value, Nothing.empty(), Nothing.empty())

def insert[T](tree: Option[Node[T]], value: T) -> Result[Node[T], str]:
    match tree:
        case Nothing():
            return Ok(leaf(value))
        case Some(node) if value == node.value:
            return Err(f"Duplicate key: {value}")
        case Some(node) if value < node.value:
            return insert(node.left, value).map(
                lambda new_left: Node(node.value, Some(new_left), node.right)
            )
        case Some(node):
            return insert(node.right, value).map(
                lambda new_right: Node(node.value, node.left, Some(new_right))
            )

def search[T](tree: Option[Node[T]], value: T) -> Option[T]:
    match tree:
        case Nothing():
            return Nothing.empty()
        case Some(node) if value == node.value:
            return Some(node.value)
        case Some(node) if value < node.value:
            return search(node.left, value)
        case Some(node):
            return search(node.right, value)
```

Building a tree from a list of values is a *fold*, not a `traverse`: each
insertion depends on the tree built by the previous one, whereas
`traverse` assumes each item maps independently. `Result.fold` (added
above) is built for exactly this - it threads an accumulator through a
sequence of steps, short-circuiting on the first `Err`, so `build_tree`
is now a one-liner:

```python
def build_tree[T](values: list[T]) -> Result[Option[Node[T]], str]:
    return Result.fold(values, Nothing.empty(), lambda tree, v: insert(tree, v).map(Some))

build_tree([5, 3, 8, 1, 4])   # Ok(Some(Node(value=5, ...)))
build_tree([5, 3, 5])         # Err('Duplicate key: 5')
```

The `.map(Some)` matters: `insert` returns `Result[Node[T], str]` (the
new node, unwrapped), but the fold's accumulator type is
`Option[Node[T]]` (the tree, which starts empty) - `.map(Some)` lifts
`insert`'s result into the accumulator's shape before `Result.fold`
feeds it into the next step.

## Adding Balance: a Red-Black Tree

The BST above can degenerate into a linked list on sorted input. Red-black
trees fix this with a coloring invariant, rebalanced on every insert.
Okasaki's purely-functional insertion algorithm (*Purely Functional Data
Structures*, 1999) is the standard reference for this without mutation or
parent pointers - just four pattern-matched rebalancing cases and a
fallback. It translates almost directly into `logerr`'s style, since
Python's `match`/`case` can destructure nested `Some(RBNode(...))`
patterns the same way Okasaki's ML/Haskell original destructures its
`Tree` constructor:

```python
from dataclasses import dataclass
from enum import Enum, auto
from logerr import Option, Some, Nothing, Result, Ok, Err

class Color(Enum):
    RED = auto()
    BLACK = auto()

@dataclass
class RBNode[T]:
    color: Color
    left: "Option[RBNode[T]]"
    value: T
    right: "Option[RBNode[T]]"

def _balance[T](
    color: Color,
    left: Option[RBNode[T]],
    value: T,
    right: Option[RBNode[T]],
) -> RBNode[T]:
    """The four Okasaki rebalancing cases, plus a fallback."""
    match (color, left, value, right):
        case (
            Color.BLACK,
            Some(RBNode(Color.RED, Some(RBNode(Color.RED, a, x, b)), y, c)),
            z,
            d,
        ):
            return RBNode(Color.RED, Some(RBNode(Color.BLACK, a, x, b)), y, Some(RBNode(Color.BLACK, c, z, d)))
        case (
            Color.BLACK,
            Some(RBNode(Color.RED, a, x, Some(RBNode(Color.RED, b, y, c)))),
            z,
            d,
        ):
            return RBNode(Color.RED, Some(RBNode(Color.BLACK, a, x, b)), y, Some(RBNode(Color.BLACK, c, z, d)))
        case (
            Color.BLACK,
            a,
            x,
            Some(RBNode(Color.RED, Some(RBNode(Color.RED, b, y, c)), z, d)),
        ):
            return RBNode(Color.RED, Some(RBNode(Color.BLACK, a, x, b)), y, Some(RBNode(Color.BLACK, c, z, d)))
        case (
            Color.BLACK,
            a,
            x,
            Some(RBNode(Color.RED, b, y, Some(RBNode(Color.RED, c, z, d)))),
        ):
            return RBNode(Color.RED, Some(RBNode(Color.BLACK, a, x, b)), y, Some(RBNode(Color.BLACK, c, z, d)))
        case _:
            return RBNode(color, left, value, right)

def _ins[T](node: Option[RBNode[T]], value: T) -> Result[RBNode[T], str]:
    match node:
        case Nothing():
            return Ok(RBNode(Color.RED, Nothing.empty(), value, Nothing.empty()))
        case Some(n) if value == n.value:
            return Err(f"Duplicate key: {value}")
        case Some(n) if value < n.value:
            return _ins(n.left, value).map(
                lambda new_left: _balance(n.color, Some(new_left), n.value, n.right)
            )
        case Some(n):
            return _ins(n.right, value).map(
                lambda new_right: _balance(n.color, n.left, n.value, Some(new_right))
            )

def rb_insert[T](tree: Option[RBNode[T]], value: T) -> Result[Option[RBNode[T]], str]:
    """Insert into a red-black tree, keeping the same Result-based
    duplicate-key contract as the plain BST above."""
    return _ins(tree, value).map(
        lambda n: Some(RBNode(Color.BLACK, n.left, n.value, n.right))
    )
```

Same recursive shape as the plain BST's `insert` - `Nothing`/`Some` for
absent/present children, `Result`/`.map()` for duplicate-key
short-circuiting - with `_balance`'s four `match`/`case` arms doing the
rebalancing work that `insert` alone doesn't need.

Building a tree from a list is the same fold as the plain BST's
`build_tree` - and since `rb_insert`'s signature already matches
`Result.fold`'s expected shape exactly (`Result[Option[RBNode[T]], str]`,
no `Node`-vs-`Option[Node]` mismatch to bridge), it needs no `.map(Some)`
wrapper at all:

```python
def rb_build_tree[T](values: list[T]) -> Result[Option[RBNode[T]], str]:
    return Result.fold(values, Nothing.empty(), rb_insert)

rb_build_tree([5, 3, 8, 1, 4, 7, 9, 2, 6, 0])   # Ok(Some(RBNode(...)))
```
