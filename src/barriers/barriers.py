"""
Python decorators for including/removing type checks, value/bounds checks, and
other code blocks within the compiled bytecode of functions and methods.
"""
from __future__ import annotations
from typing import Callable
import doctest
import textwrap
import ast
import inspect

class barriers(dict): # pylint: disable=too-few-public-methods
    """
    Class for per-module configuration objects that can be used to define and
    toggle inclusion of categories of checks, for decorating functions, and for
    marking code blocks.

    Consider the function below. The body of this function contains a code
    block that raises an exception if either of the two inputs is a negative
    integer.

    >>> def f(x: int, y: int) -> int:
    ...
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...     return x + y
    ...
    >>> f(1, 2)
    3
    >>> f(-1, -2)
    Traceback (most recent call last):
      ...
    ValueError: inputs must be nonnegative

    Below, an instance of :obj:`~barriers.barriers.barriers` is introduced. The
    instance *must be called* ``barriers``. The constructor adds an entry to
    ``globals()`` for the instance being constructed; the examples in this
    docstring cannot modify ``globals()`` in this way and so the instance is
    explicitly assigned to the variable ``barriers``.

    >>> from barriers import barriers
    >>> barriers = barriers()

    The :obj:`~barriers.barriers.barriers` instance defined above is now a
    decorator that transforms any decorated function by removing any statement
    that appears directly below any instance of a *marker*. A statement can be
    designated for automatic removal by placing a marker -- the ``barriers``
    variable -- on the line directly above that statement.

    >>> @barriers
    ... def f(x: int, y: int) -> int:
    ...
    ...     barriers
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...     return x + y
    ...

    Note that in the body of the function ``f`` defined above, the ``if`` block
    is immediately preceded by a line that contains the variable ``barriers``.
    Thus, the decorator ``@barriers`` automatically removed the ``if`` block.
    As a result, the function does not raise an exception when it is applied to
    negative inputs.

    >>> f(1, 2)
    3
    >>> f(-1, -2)
    -3

    It is possible to explicitly supply the namespace (such as the one that
    corresponds to the local scope) to the decorator. This may be necessary to
    do if the body of the function contains symbols that only appear in the
    supplied namespace. For example, suppose the function below has been
    defined.

    >>> def g(x, y):
    ...     return x + y

    The definition of the function ``f`` below refers to the function ``g``
    defined above. However, invoking the decorated function raises an exception.

    >>> @barriers
    ... def f(x: int, y: int) -> int:
    ...
    ...     barriers
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...     return g(x, y)
    ...
    >>> f(1, 2)
    Traceback (most recent call last):
      ...
    NameError: name 'g' is not defined

    The :obj:`__getitem__` method allows bracket notation to be used
    in order to supply a symbol table for a namespace.

    >>> @barriers[locals()]
    ... def f(x: int, y: int) -> int:
    ...
    ...     barriers
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...     return g(x, y)
    ...
    >>> f(1, 2)
    3
    >>> f(-1, -2)
    -3

    Note that the :obj:`__call__` method uses the namespace returned by
    :obj:`globals`. Thus, the decorator ``@barriers`` is equivalent to
    ``@barriers[globals()]``. However, in certain situations (*e.g.*, in
    doctests) this is not sufficient.
    """
    def __init__(self: barriers):
        super().__init__()
        globals()['barriers'] = self

    def _transform(self: barriers, function: Callable, namespace: dict) -> Callable:
        """
        Transform a function by removing any statement within the body that has a
        marker that appears immediately above it.
        """
        # Parse the function definition into an abstract syntax tree.
        a = ast.parse(textwrap.dedent(inspect.getsource(function)))

        # Transform the abstract syntax tree.
        statements = a.body[0].body
        statements_ = [] # New function body.

        i = 0
        while i < len(statements):
            if (
                isinstance(statements[i], ast.Expr) and
                isinstance(statements[i].value, ast.Name) and
                (statements[i].value.id == 'barriers') and
                i <= (len(statements) - 1) # Remove mark if it appears last.
            ):
                i += 2
                continue

            statements_.append(statements[i])
            i += 1

        a.body[0].body = statements_

        # Compile and execute the transformed function definition given a
        # namespace symbol table.
        exec( # pylint: disable=exec-used
            compile(a, '<string>', 'exec'),
            namespace
        )

        return namespace[function.__name__]

    def __getitem__(self: barriers, namespace: dict) -> Callable[[Callable], Callable]:
        """
        Decorator that parses a function and removes any marked code blocks as
        specified within this instance.
        """
        def decorator(function: Callable, namespace: dict = namespace) -> Callable:
            """
            Decorator that is applied to the function to be transformed.
            """
            namespace = dict(namespace.items())
            namespace['barriers'] = _substitute() # Avoid transforming recursively.
            return self._transform(function, namespace)

        return decorator

    def __call__(self: barriers, function: Callable) -> Callable:
        """
        Decorator that parses a function and removes any marked code blocks as
        specified within this instance.
        """
        namespace = dict(globals().items()) # Use the global namespace by default.
        namespace['barriers'] = _substitute() # Avoid transforming recursively.
        return self._transform(function, namespace)

class _substitute(barriers): # pylint: disable=invalid-name # Exclude from documentation.
    """
    Class for creating placeholder instances of :obj:`~barriers.barriers.barriers`
    that have no effect. Instances of this class are introduced in place of the
    user-defined instance in order to avoid recursive invocation of a
    :obj:`~barriers.barriers.barriers` instance during the execution of a modified
    abstract syntax tree.
    """
    def __getitem__(self: _substitute, namespace: dict) -> Callable[[Callable], Callable]:
        """
        Discard supplied namespace and return a decorator.
        """
        return lambda function: function

    def __call__(self: _substitute, function: Callable) -> Callable:
        """
        Return the supplied function.
        """
        return function

if __name__ == '__main__':
    doctest.testmod() # pragma: no cover
