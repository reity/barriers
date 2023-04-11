"""
Python decorators for including/excluding type checks, value/bounds checks, and
other code blocks within the compiled bytecode of functions and methods.
"""
from __future__ import annotations
from typing import Tuple, Optional, Callable, Dict
import doctest
import sys
import textwrap
import ast
import inspect

class barriers: # pylint: disable=too-few-public-methods
    """
    Class for per-module configuration objects that can be used to define
    (and toggle inclusion of) categories of code blocks, to decorate functions,
    and to mark code blocks.

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

    Below, an instance of :obj:`~barriers.barriers.barriers` is introduced.

    >>> from barriers import barriers
    >>> example = barriers(False) @ globals()

    The :obj:`~barriers.barriers.barriers` instance ``example`` defined above
    is a decorator that can remove designated code blocks in the body of a
    function.

      * The ``False`` argument in the expression ``barriers(False)`` above should
        be interpreted to mean that **this barrier is disabled** (*i.e.*, that the
        marked code blocks in the bodies of functions decorated by this decorator
        should be removed). The default value for this optional argument is
        ``True``; this should be interpreted to mean that **this barrier is
        enabled** (and, thus, that marked code blocks should not be removed from
        decorated functions).

      * The notation ``@ globals()`` ensures that the namespace returned by
        :obj:`globals` is used when compiling the abstract syntax trees of
        transformed functions.

    A code block can be designated for automatic removal by placing a marker --
    in this case, the ``example`` variable -- on the line directly above that
    code block. Note that in the body of the function ``f`` defined below, the
    ``if`` block is immediately preceded by a line that contains the variable
    ``example``.

    >>> @example
    ... def f(x: int, y: int) -> int:
    ...
    ...     example
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...     return x + y

    The decorator ``@example`` automatically removes the ``if`` block in the
    function above. As a result, the function does not raise an exception when
    it is applied to negative inputs.

    >>> f(1, 2)
    3
    >>> f(-1, -2)
    -3

    It is also possible to use the string literal ``'example'`` as a marker.

    >>> @example
    ... def g(x: int, y: int) -> int:
    ...
    ...     'example'
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...     return x + y

    This may be preferable because string literals appearing as statements do
    not contribute to the size of the compiled bytecode of a function (as shown
    below).

    >>> def f(x: int, y: int) -> int:
    ...     example
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...     return x + y
    ...
    >>> def g(x: int, y: int) -> int:
    ...     'example'
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...     return x + y
    ...
    >>> from dis import Bytecode
    >>> len(list(Bytecode(g.__code__))) < len(list(Bytecode(f.__code__)))
    True

    It is also possible to define and use individually named markers (which
    are created as attributes of the :obj:`~barriers.barriers.barriers`
    instance).

    >>> from barriers import barriers
    >>> checks = barriers(types=True, bounds=False) @ globals()
    >>> @checks
    ... def f(x: int, y: int) -> int:
    ...
    ...     checks.types
    ...     if not isinstance(x, int) and not isinstance(y, int):
    ...         raise TypeError('inputs must be integers')
    ...
    ...     checks.bounds
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...     return x + y
    ...
    >>> f('a', 'b')
    Traceback (most recent call last):
      ...
    TypeError: inputs must be integers
    >>> f(-1, -2)
    -3

    When one or more named markers are defined, only named markers that have
    been defined can be used.

    >>> @checks
    ... def h(x: int) -> int:
    ...
    ...     checks
    ...     if x == 0:
    ...         raise ValueError('value must be nonzero')
    ...
    ...     return x
    ...
    Traceback (most recent call last):
      ...
    RuntimeError: cannot use general marker when individual markers are defined
    >>> @checks
    ... def h(x: int) -> int:
    ...
    ...     checks.value
    ...     if x == 0:
    ...         raise ValueError('value must be nonzero')
    ...
    ...     return x
    ...
    Traceback (most recent call last):
      ...
    NameError: marker `checks.value` is not defined
    >>> @checks
    ... def h(x: int) -> int:
    ...
    ...     'checks.value'
    ...     if x == 0:
    ...         raise ValueError('value must be nonzero')
    ...
    ...     return x
    ...
    Traceback (most recent call last):
      ...
    NameError: marker `checks.value` is not defined

    A statement may have a syntactic form that *could* be a marker. However,
    if it makes no reference to a defined instance of
    :obj:`~barriers.barriers.barriers`, it is ignored.

    >>> @checks
    ... def h(x: int) -> int:
    ...
    ...     undefined.value
    ...     if x == 0:
    ...         raise ValueError('value must be nonzero')
    ...
    ...     return x

    If a string marker cannot be parsed as an expression, it is ignored.

    >>> @checks
    ... def i(x: int, y: int) -> int:
    ...
    ...     'checks!value'
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...     'pass'
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...     return x + y
    ...
    >>> i(-1, -2)
    Traceback (most recent call last):
      ...
    ValueError: inputs must be nonnegative

    When defining individual markers, setting the status using a single boolean
    argument is not possible. Also, only a single boolean argument is permitted.

    >>> from barriers import barriers
    >>> checks = barriers(True, types=True, bounds=False)
    Traceback (most recent call last):
      ...
    ValueError: cannot specify general status when defining individual markers
    >>> from barriers import barriers
    >>> checks = barriers(True, False)
    Traceback (most recent call last):
      ...
    ValueError: exactly one status argument or one or more named status arguments are required

    In order to accommodate the remaining examples, the statement below resets
    the :obj:`~barriers.barriers.barriers` instance to one that does not define
    distinct, named markers.

    >>> from barriers import barriers
    >>> checks = barriers(False) @ globals()

    Decorators can be applied to functions that invoke other functions. For
    example, the definition of the function ``f`` below refers to another
    function ``g``.

    >>> def g(x, y):
    ...     return x + y
    ...
    >>> @checks
    ... def f(x: int, y: int) -> int:
    ...
    ...     checks
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...     return g(x, y)
    ...
    >>> f(1, 2)
    3

    For completess, the example below demonstrates that marked code blocks
    are by default (*i.e.*, when no arguments are supplied to the
    :obj:`~barriers.barriers.barriers` constructor) not removed.

    >>> from barriers import barriers
    >>> checks = barriers() @ globals()
    >>> def f(x: int, y: int) -> int:
    ...
    ...     checks
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...     return x + y
    ...
    >>> f(-1, -2)
    Traceback (most recent call last):
      ...
    ValueError: inputs must be nonnegative

    The ``>>`` operator (corresponding to the :obj:`__rshift__` method) can
    be used to ensure that the decorator stores the transformed version of the
    decorated function under a specific attribute.

    >>> from barriers import barriers
    >>> checks = barriers(False) @ globals() >> 'unsafe'

    Note that in the example below, the decorator has no effect on the original
    function ``f``. However, the function ``f.unsafe`` corresponds to the
    transformed version of ``f``.

    >>> def g(x, y):
    ...     return x + y
    ...
    >>> @checks
    ... def f(x: int, y: int) -> int:
    ...
    ...     checks
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...     return g(x, y)
    ...
    >>> f(-1, -2)
    Traceback (most recent call last):
      ...
    ValueError: inputs must be nonnegative
    >>> f.unsafe(-1, -2)
    -3

    The ``<<`` operator (corresponding to the :obj:`__lshift__` method) behaves
    in a complementary manner. After this method has been invoked, the decorater
    transforms a decorated function but preserves the original function under
    the specified attribute.
    """
    def __init__(
            self: barriers,
            *args: Optional[Tuple[bool]],
            **kwargs: Optional[Dict[str, bool]]
        ):
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

        # Used to avoid recursive transformations.
        self._disabled = False

        # Attribute of a decorated function under under which the transformed
        # function is stored. If this is ``None``, then the function itself
        # is transformed.
        self._attribute = None

        # Default namespace to use when compiling transformed abstract syntax
        # trees of functions.
        self._namespace = {}

    def __matmul__(self: barriers, namespace: dict) -> barriers:
        """
        Store internally the supplied namespace. This namespace is used during
        the compilation of transformed abstract syntax trees of functions in
        the :obj:`_transform` method.

        >>> from barriers import barriers
        >>> example = barriers(False) @ globals()
        >>> @example
        ... def f(x: int, y: int) -> int:
        ...
        ...     example
        ...     if x < 0 or y < 0:
        ...         raise ValueError('inputs must be nonnegative')
        ...
        ...     return x + y
        ...
        >>> f(-1, -2)
        -3

        If no namespace is specified, it is possible that instances of markers
        that appear in the body of a function will not be recognized.

        >>> from barriers import barriers
        >>> example = barriers(False)
        >>> @example
        ... def f(x: int, y: int) -> int:
        ...
        ...     example
        ...     if x < 0 or y < 0:
        ...         raise ValueError('inputs must be nonnegative')
        ...
        ...     return x + y
        ...
        Traceback (most recent call last):
           ...
        NameError: name 'example' is not defined
        """
        self._namespace = namespace
        return self

    def __rshift__(self: barriers, attribute: str) -> barriers:
        """
        Set the attribute (of decorated function objects) under which the
        transformed versions of functions should be stored. After this method
        has been invoked, this decorator will not change the decorated function
        itself.

        >>> from barriers import barriers
        >>> checks = barriers(False) @ globals() >> 'unsafe'
        >>> @checks
        ... def f(x: int, y: int) -> int:
        ...
        ...     checks
        ...     if x < 0 or y < 0:
        ...         raise ValueError('inputs must be nonnegative')
        ...
        ...     return x + y
        ...
        >>> f(-1, -2)
        Traceback (most recent call last):
          ...
        ValueError: inputs must be nonnegative
        >>> f.unsafe(-1, -2)
        -3
        """
        self._attribute = (True, attribute)
        return self

    def __lshift__(self: barriers, attribute: str) -> barriers:
        """
        Set the attribute (of decorated function objects) under which the
        original versions of functions should be stored. After this method has
        been invoked, this decorator will always store the original (unmodified)
        function under the specified attribute.

        >>> from barriers import barriers
        >>> checks = barriers(False) @ globals() << 'safe'
        >>> @checks
        ... def f(x: int, y: int) -> int:
        ...
        ...     checks
        ...     if x < 0 or y < 0:
        ...         raise ValueError('inputs must be nonnegative')
        ...
        ...     return x + y
        ...
        >>> f(-1, -2)
        -3
        >>> f.safe(-1, -2)
        Traceback (most recent call last):
          ...
        ValueError: inputs must be nonnegative
        """
        self._attribute = (False, attribute)
        return self

    def _marker(self: barriers, s: ast.Stmt, namespace: dict) -> bool:
        """
        Return a boolean value indicating whether the supplied expression is a
        marker that indicates (according to the configuration of this instance)
        that the marked code blocks should be removed.
        """
        if isinstance(s, ast.Expr):

            # If the marker is a string, attempt to parse that string.
            # Accommodate Python 3.7 AST classes.
            string = None
            if sys.version_info < (3, 8) and isinstance(s.value, ast.Str):
                string = s.value.s # pragma: no cover
            elif isinstance(s.value, ast.Constant) and isinstance(s.value.value, str):
                string = s.value.value # pragma: no cover

            if string is not None:
                try:
                    s = ast.parse(string).body[0]
                    if not isinstance(s, ast.Expr):
                        return False
                except SyntaxError as _:
                    return False

            # Simple universal marker.
            if (
                isinstance(s.value, ast.Name) and
                (namespace.get(s.value.id, None) == self)
            ):
                if len(self.configuration) > 0:
                    raise RuntimeError(
                        'cannot use general marker when individual markers are defined'
                    )

                return not self.status # Remove marked code block if barriers are disabled.

            # Named marker.
            if (
                isinstance(s.value, ast.Attribute) and
                isinstance(s.value.value, ast.Name) and
                (namespace.get(s.value.value.id, None) == self)
            ):
                # All individual markers must be defined in the configuration.
                if s.value.attr not in self.configuration:
                    raise NameError(
                        'marker `' +
                        s.value.value.id + '.' + s.value.attr +
                        '` is not defined'
                    )

                # Remove marked code block if barriers for this individual marker
                # are disabled.
                return not self.configuration[s.value.attr]

        return False

    def _transform(self: barriers, function: Callable, namespace: dict) -> Callable:
        """
        Transform a function by removing any statement within the body that has a
        marker that appears immediately above it.
        """
        if self._disabled: # Avoid transforming when executing compiled bytecode.
            return function

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
                if self._marker(statements[i], namespace):
                    i += 2
                    continue

                statements_.append(statements[i])
                i += 1

            a.body[0].body = statements_

        # Compile and execute the transformed function definition given a
        # namespace symbol table.
        self._disabled = True # Avoid transforming recursively.
        try:
            exec( # pylint: disable=exec-used
                compile(a, '<string>', 'exec'),
                namespace
            )
            self._disabled = False
        except Exception as e: # pragma: no cover
            # If an exception is raised during compilation and execution,
            # restore the state of this instance before raising the exception.
            self._disabled = False
            raise e

        # Either store the transformed function under an attribute of the
        # function object and return the function unmodified, or store
        # the unmodified function as an attribute of the transformed function
        # (in which case the transformed function is returned, as usual).
        if isinstance(self._attribute, tuple):
            if self._attribute[0]:
                setattr(
                    function,
                    self._attribute[1],
                    namespace[function.__name__]
                )
                return function

            # Store unmodified function as an attribute of the transformed
            # function. The transformed function will be returned by the
            # last statement in this method (as is the default behavior).
            setattr(namespace[function.__name__], self._attribute[1], function)

        result = namespace[function.__name__]
        result.__name__ = function.__name__ # Preserve original function's name.
        result.__doc__ = function.__doc__ # Preserve original function's docstring.
        return result

    def __call__(self: barriers, function: Callable) -> Callable:
        """
        Allows this instance to behave as a decorator that parses a function
        and removes any marked code blocks (as specified within this instance).

        >>> from barriers import barriers
        >>> example = barriers(False) @ globals()
        >>> @example
        ... def f(x: int, y: int) -> int:
        ...
        ...     example
        ...     if x < 0 or y < 0:
        ...         raise ValueError('inputs must be nonnegative')
        ...
        ...     return x + y
        ...
        >>> f(-1, -2)
        -3
        """
        return self._transform(function, self._namespace)

if __name__ == '__main__':
    doctest.testmod() # pragma: no cover
