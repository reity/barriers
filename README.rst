========
barriers
========

Python decorators for including/excluding type checks, value/bounds checks, and other code blocks within the compiled bytecode of functions and methods.

|pypi| |readthedocs| |actions| |coveralls|

.. |pypi| image:: https://badge.fury.io/py/barriers.svg
   :target: https://badge.fury.io/py/barriers
   :alt: PyPI version and link.

.. |readthedocs| image:: https://readthedocs.org/projects/barriers/badge/?version=latest
   :target: https://barriers.readthedocs.io/en/latest/?badge=latest
   :alt: Read the Docs documentation status.

.. |actions| image:: https://github.com/reity/barriers/workflows/lint-test-cover-docs/badge.svg
   :target: https://github.com/reity/barriers/actions/workflows/lint-test-cover-docs.yml
   :alt: GitHub Actions status.

.. |coveralls| image:: https://coveralls.io/repos/github/reity/barriers/badge.svg?branch=main
   :target: https://coveralls.io/github/reity/barriers?branch=main
   :alt: Coveralls test coverage summary.

Installation and Usage
----------------------
This library is available as a `package on PyPI <https://pypi.org/project/barriers>`__::

    python -m pip install barriers

The library can be imported in the usual ways::

    import barriers
    from barriers import barriers

Examples
^^^^^^^^

.. |barriers| replace:: ``barriers``
.. _barriers: https://barriers.readthedocs.io/en/0.1.0/_source/barriers.html#barriers.barriers.barriers

.. |globals| replace:: ``globals``
.. _globals: https://docs.python.org/3/library/functions.html#globals

Consider the function below. The body of this function contains a code block that raises an exception if either of the two inputs is a negative integer::

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

An instance of the |barriers|_ class should normally be introduced near the top of a Python module::

    >>> example = barriers(False) @ globals() # Remove marked code blocks (i.e., "disable barriers").

The |barriers|_ instance ``example`` defined above is a decorator that transforms any decorated function by removing any designated code blocks in the body of that function.

* The ``False`` argument in the expression ``barriers(False)`` above should be interpreted to mean that **this barrier is disabled** (*i.e.*, that the marked code blocks in the bodies of functions decorated by this decorator **should be removed**). The default value for this optional argument is ``True``; this should be interpreted to mean that **this barrier is enabled** (and, thus, that marked code blocks **should not be removed** from decorated functions).

* The notation ``@ globals()`` ensures that the namespace returned by |globals|_ is used when compiling the abstract syntax trees of transformed functions.

A statement can be designated for automatic removal by placing a marker -- in this case, the ``example`` variable -- on the line directly above that statement. Note that in the body of the function ``f`` defined below, the ``if`` block is immediately preceded by a line that contains the variable ``example``::

    >>> @example
    ... def f(x: int, y: int) -> int:
    ...
    ...     example
    ...     if x < 0 or y < 0:
    ...         raise ValueError('inputs must be nonnegative')
    ...
    ...     return x + y

The decorator ``@example`` automatically removes the ``if`` block in the function above. As a result, the function does not raise an exception when it is applied to negative inputs::

    >>> f(1, 2)
    3
    >>> f(-1, -2)
    -3

It is also possible to define and use individually named markers (which are created as attributes of the |barriers|_ instance)::

    >>> from barriers import barriers
    >>> checks = barriers(types=True, bounds=False) @ globals()

Given the above definitions, it is now possible to introduce named markers such as those in the example below. When a marker definition has been assigned ``True``, the statements immediately below that named marker **are not removed** (*i.e.*, the marked barrier statements are enabled). When a marker definition has been assigned ``False``, the corresponding marked statements **are removed**::

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

Many additional details and examples are presented in the `documentation <https://barriers.readthedocs.io/en/0.1.0>`__.

Development
-----------
All installation and development dependencies are fully specified in ``pyproject.toml``. The ``project.optional-dependencies`` object is used to `specify optional requirements <https://peps.python.org/pep-0621>`__ for various development tasks. This makes it possible to specify additional options (such as ``docs``, ``lint``, and so on) when performing installation using `pip <https://pypi.org/project/pip>`__::

    python -m pip install .[docs,lint]

Documentation
^^^^^^^^^^^^^
The documentation can be generated automatically from the source files using `Sphinx <https://www.sphinx-doc.org>`__::

    python -m pip install .[docs]
    cd docs
    sphinx-apidoc -f -E --templatedir=_templates -o _source .. && make html

Testing and Conventions
^^^^^^^^^^^^^^^^^^^^^^^
All unit tests are executed and their coverage is measured when using `pytest <https://docs.pytest.org>`__ (see the ``pyproject.toml`` file for configuration details)::

    python -m pip install .[test]
    python -m pytest

Alternatively, all unit tests are included in the module itself and can be executed using `doctest <https://docs.python.org/3/library/doctest.html>`__::

    python src/barriers/barriers.py -v

Style conventions are enforced using `Pylint <https://pylint.pycqa.org>`__::

    python -m pip install .[lint]
    python -m pylint src/barriers

Contributions
^^^^^^^^^^^^^
In order to contribute to the source code, open an issue or submit a pull request on the `GitHub page <https://github.com/reity/barriers>`__ for this library.

Versioning
^^^^^^^^^^
The version number format for this library and the changes to the library associated with version number increments conform with `Semantic Versioning 2.0.0 <https://semver.org/#semantic-versioning-200>`__.

Publishing
^^^^^^^^^^
This library can be published as a `package on PyPI <https://pypi.org/project/barriers>`__ by a package maintainer. First, install the dependencies required for packaging and publishing::

    python -m pip install .[publish]

Ensure that the correct version number appears in ``pyproject.toml``, and that any links in this README document to the Read the Docs documentation of this package (or its dependencies) have appropriate version numbers. Also ensure that the Read the Docs project for this library has an `automation rule <https://docs.readthedocs.io/en/stable/automation-rules.html>`__ that activates and sets as the default all tagged versions. Create and push a tag for this version (replacing ``?.?.?`` with the version number)::

    git tag ?.?.?
    git push origin ?.?.?

Remove any old build/distribution files. Then, package the source into a distribution archive::

    rm -rf build dist src/*.egg-info
    python -m build --sdist --wheel .

Finally, upload the package distribution archive to `PyPI <https://pypi.org>`__::

    python -m twine upload dist/*
