"""
Python decorator for including/removing type checks, value/bounds checks, and
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
    >>> barriers = barriers(False) # Remove marked statements (i.e., "disable barriers").

    The :obj:`~barriers.barriers.barriers` instance defined above is now a
    decorator that transforms any decorated function by removing any statement
    that appears directly below any instance of a *marker*. A statement can be
    designated for automatic removal by placing a marker -- the ``barriers``
    variable -- on the line directly above that statement.

    The ``False`` argument in the expression ``barriers(False)`` above should
    be interpreted to mean that *barriers are disabled* (*i.e.*, that the
    barrier statements should be removed). The default value for this optional
    argument is ``True``; this should be interpreted to mean that *barriers
    are enabled* (and, thus, that marked statements should not be removed from
    decorated functions).

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

    It is also possible to use the string literal ``'barriers'`` as a marker.

    >>> @barriers
    ... def g(x: int, y: int) -> int:
    ...
    ...     'barriers'
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...     return x + y
    ...

    This may be preferable because string literals appearing as statements do
    not contribute to the size of the compiled bytecode of a function (as shown
    below).

    >>> def f(x: int, y: int) -> int:
    ...     barriers
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...     return x + y
    >>> def g(x: int, y: int) -> int:
    ...     'barriers'
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...     return x + y
    >>> from dis import Bytecode
    >>> len(list(Bytecode(g.__code__))) < len(list(Bytecode(f.__code__)))
    True

    It is also possible to define and use individually named markers (which
    are referenced as attributes of the :obj:`~barriers.barriers.barriers`
    instance).

    >>> from barriers import barriers
    >>> barriers = barriers(type=True, bounds=False)
    >>> @barriers
    ... def f(x: int, y: int) -> int:
    ...
    ...     barriers.type
    ...     if not isinstance(x, int) and not isinstance(y, int):
    ...         raise TypeError('inputs must be integers')
    ...
    ...     barriers.bounds
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...     return x + y
    >>> f('a', 'b')
    Traceback (most recent call last):
      ...
    TypeError: inputs must be integers
    >>> f(-1, -2)
    -3

    When one or more named markers are defined, only named markers that have
    been defined can be used.

    >>> @barriers
    ... def h(x: int) -> int:
    ...
    ...     barriers
    ...     if x == 0:
    ...         raise ValueError('value must be nonzero')
    ...
    ...     return x
    Traceback (most recent call last):
      ...
    RuntimeError: cannot use general marker when individual markers are defined
    >>> @barriers
    ... def h(x: int) -> int:
    ...
    ...     barriers.value
    ...     if x == 0:
    ...         raise ValueError('value must be nonzero')
    ...
    ...     return x
    Traceback (most recent call last):
      ...
    RuntimeError: marker `barriers.value` is not defined
    >>> @barriers
    ... def h(x: int) -> int:
    ...
    ...     'barriers.value'
    ...     if x == 0:
    ...         raise ValueError('value must be nonzero')
    ...
    ...     return x
    Traceback (most recent call last):
      ...
    RuntimeError: marker `barriers.value` is not defined

    If a string marker cannot be parsed as an expression, it is ignored.

    >>> @barriers
    ... def i(x: int, y: int) -> int:
    ...
    ...     'barriers!value'
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...     'pass'
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...     return x + y
    >>> i(-1, -2)
    Traceback (most recent call last):
      ...
    ValueError: inputs must be nonnegative

    When defining individual markers, setting the status using a single boolean
    argument is not possible. Also, only a single boolean argument is permitted.

    >>> from barriers import barriers
    >>> barriers = barriers(True, type=True, bounds=False)
    Traceback (most recent call last):
      ...
    ValueError: cannot specify general status when defining individual markers
    >>> from barriers import barriers
    >>> barriers = barriers(True, False)
    Traceback (most recent call last):
      ...
    ValueError: exactly one status argument or one or more named ... required

    In order to accommodate the remaining example, the statement below resets
    the :obj:`~barriers.barriers.barriers` instance to one that does not define
    distinct, named markers.

    >>> from barriers import barriers
    >>> barriers = barriers(False)

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

    In Python 3.9 and later, the :obj:`__getitem__` method allows bracket
    notation to be used in order to supply a symbol table for a namespace.
    The example below invokes this method explicitly in order accommodate
    the syntax supported in Python 3.7 and Python 3.8.

    >>> @barriers.__getitem__(locals()) # Or ``@barriers[locals()]`` in Python 3.9 or later.
    ... def f(x: int, y: int) -> int:
    ...
    ...    barriers
    ...    if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...    return g(x, y)
    >>> f(1, 2)
    3
    >>> f(-1, -2)
    -3

    Note that the :obj:`__call__` method uses the namespace returned by
    :obj:`globals`. Thus, the decorator ``@barriers`` is equivalent to
    ``@barriers[globals()]``. However, in certain situations (*e.g.*, in
    doctests) this is not sufficient.

    For completess, the example below demonstrates that marked statements
    are not removed when the default configuration is used.

    >>> from barriers import barriers
    >>> barriers = barriers() # Equivalent to ``barriers(True)``.
    >>> def f(x: int, y: int) -> int:
    ...
    ...     barriers
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...     return x + y
    ...
    >>> f(-1, -2)
    Traceback (most recent call last):
      ...
    ValueError: inputs must be nonnegative
    """
    def __init__(self: barriers, *args, **kwargs):
        super().__init__()

        if len(kwargs) > 0 and len(args) > 0:
            raise ValueError(
                'cannot specify general status when defining individual markers'
            )

        if len(args) == 0 and len(kwargs) == 0:
            self.status = True

        if len(args) == 0 and len(kwargs) > 0:
            self.status = None

        if len(args) > 0 and len(kwargs) == 0:
            if len(args) > 1:
                raise ValueError(
                    'exactly one status argument or one or more named ' +
                    'status arguments are required'
                )

            self.status = args[0]

        # Store the configuration and add attributes to this instance that
        # correspond to the named markers.
        self.configuration = kwargs
        for (name, status) in kwargs.items():
            setattr(self, name, status)

        # Only one instance of this class should be created in a module.
        globals()['barriers'] = self

    def _marker(self: barriers, s: ast.Stmt) -> bool:
        """
        Return a boolean value indicating whether the supplied expression is a
        marker that indicates (according to the configuration of this instance)
        that the marked statement should be removed.
        """
        if isinstance(s, ast.Expr):

            # If the marker is a string, attempt to parse that string.
            if isinstance(s.value, ast.Constant) and isinstance(s.value.value, str):
                try:
                    s = ast.parse(s.value.value).body[0]
                    if not isinstance(s, ast.Expr):
                        return False
                except SyntaxError as _:
                    return False

            # Simple universal marker.
            if isinstance(s.value, ast.Name) and (s.value.id == 'barriers'):
                if len(self.configuration) > 0:
                    raise RuntimeError(
                        'cannot use general marker when individual markers are defined'
                    )

                return not self.status # Remove marked statement if barriers are disabled.

            # Named marker.
            if (
                isinstance(s.value, ast.Attribute) and
                isinstance(s.value.value, ast.Name) and
                (s.value.value.id == 'barriers')
            ):
                # All individual markers must be defined in the configuration.
                if s.value.attr not in self.configuration:
                    raise RuntimeError(
                        'marker `barriers.' + s.value.attr + '` is not defined'
                    )

                # Remove marked statement if barriers for this individual marker
                # are disabled.
                return not self.configuration[s.value.attr]

        return False

    def _transform(self: barriers, function: Callable, namespace: dict) -> Callable:
        """
        Transform a function by removing any statement within the body that has a
        marker that appears immediately above it.
        """
        # Parse the function definition into an abstract syntax tree.
        a = ast.parse(textwrap.dedent(inspect.getsource(function)))

        # Transform the abstract syntax tree if all barriers are disabled
        # or if named markers have been defined (and must be checked
        # individually).
        if self.status is False or len(self.configuration) > 0:
            statements = a.body[0].body
            statements_ = [] # New function body.

            # Iterate over the statements and skip two statements (the marker
            # and the statement below it) whenever a marker is detected. If
            # a marker appears as the last statement, it is removed.
            i = 0
            while i < len(statements):
                if self._marker(statements[i]):
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
    def __getattr__(self: _substitute, name: str):
        """
        Ensure that named markers do not cause errors during compilation.
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
