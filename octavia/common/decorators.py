#    Copyright 2016
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Decorators to provide backwards compatibility for V1 API."""


def rename_kwargs(**renamed_kwargs):
    """Renames a class's variables and maintains backwards compatibility.

    :param renamed_kwargs: mapping of old kwargs to new kwargs.  For example,
                           to say a class has renamed variable foo to bar the
                           decorator would be used like:
                           rename_kwargs(foo='bar')

    """

    def wrap(cls):
        def __getattr__(instance, name):
            if name in renamed_kwargs:
                return getattr(instance, renamed_kwargs[name])
            return getattr(instance, name)

        def __setattr__(instance, name, value):
            if name in renamed_kwargs:
                instance.__dict__[renamed_kwargs[name]] = value
            else:
                instance.__dict__[name] = value

        def wrapped_cls(*args, **kwargs):
            # Handle cases of inner classes being called with self
            # For example: self.TestClass(1, a=1)
            if (args and hasattr(args[0], '__class__') and
                    hasattr(args[0].__class__, cls.__name__)):
                args = args[1:] if args else tuple()
            for old_kwarg, new_kwarg in renamed_kwargs.items():
                if old_kwarg in kwargs:
                    kwargs[new_kwarg] = kwargs[old_kwarg]
                    del kwargs[old_kwarg]
            cls.__getattr__ = __getattr__
            cls.__setattr__ = __setattr__
            return cls(*args, **kwargs)
        return wrapped_cls
    return wrap
