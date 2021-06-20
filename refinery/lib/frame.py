#!/usr/bin/env python3
# -*- coding: utf-8 -*-
R"""
Some refinery units produce more than one output when applied to an input. For example,
`refinery.chop` will chop the input data into evenly sized blocks and emit each of them
as a single output. By default, if no framing syntax is used, multiple outputs are
separated by line breaks, which is often desirable when text data is extracted. However,
for processing binary data, this is equally often more than useless. To process the list
of results generated by any refinery unit, end the command for this unit with the
special argument `[`. This argument has to be the last argument to be recognized as a
framing initialization. If this syntax is used, the list of results is emitted in an
internal format which allows arbitrarily nested lists of binary chunks to be processed.

### Simple Frame Example

    $ emit OOOOOOOO | chop 2 [| ccp F | cca . ]
    FOO.FOO.FOO.FOO.

Here, the string `OOOOOOOO` is first chopped into blocks of 2, yielding the **frame**
`[OO, OO, OO, OO]` which is then forwarded to the next command. If a `refinery.units.Unit`
receives input in framed format, each chunk of the frame is processed individually and
emitted as one output chunk. In this case, `refinery.ccp` simply prepends `F` to every
input, producing the frame `[FOO, FOO, FOO, FOO]`. Finally, `refinery.cca` appends a period
to each chunk. When a unit is given the closing bracket as the last argument, this
concludes processing of one frame which results in concatenation of all binary chunks in
the frame.

### Frame Layers

Frames can be nested arbitrarily, and `refinery.sep` can be used to insert a separator
(the default is line break) between all chunks in the frame:

    $ emit OOOOOOOO | chop 4 [| chop 2 [| ccp F | cca . ]| sep ]
    FOO.FOO.
    FOO.FOO.

Here, we first produce the two-layered **frame tree** `[[OO,OO], [OO,OO]]` by using two
`refinery.chop` invocations. We refer to this data as a tree because, well, it is one:

    LAYER 1:      [[..],[..]]
                    /     \
    LAYER 2:    [OO,OO] [OO,OO]

The bottom layer is processed as before, yielding `[FOO.FOO., FOO.FOO.]`. Next, the unit
`refinery.sep` inserts a line break character between the two chunks in this frame.

### Adding Line Breaks Easily

Since separating data with line breaks is a common requirement, it is also possible to use
one more closing bracket than necessary at the end of a frame to separate all chunks by line
breaks:

    $ emit OOOOOOOO | chop 4 [| chop 2 [| ccp F | cca . ]]]
    FOO.FOO.
    FOO.FOO.

### Squeezing

Inside a frame, application of a `refinery.units.Unit` with multiple outputs will substitute the
input by the corresponding list of outputs. For example,

    $ emit OOOOOOOO | chop 4 [| chop 2 | ccp F ]]

has the exact same output as the following command:

    $ emit 00000000 | chop 2 [| ccp F ]]

In the first case, we create the frame `[OOOO, OOOO]` and then apply `chop 2` to each chunk,
which results in the frame `[OO, OO, OO, OO]`. Now, consider the example

    $ emit OOCLOOCL | chop 4 [| snip 2::-1 3: ]]
    COO
    L
    COO
    L

With what we have learned so far, if we wanted it to spell `COOL` twice instead,we would have
to use the following and slightly awkward syntax:

    $ emit OOCLOOCL | chop 4 [| snip 2::-1 3 [| nop ]| sep ]
    COOL
    COOL

This is because the `snip` command, by default, will simply insert the list `[COO, L]` into
the complete frame, creating the output sequence `[COO, L, COO, L]` and all of these chunks
will be separated by line breaks. For this reason, the squeeze syntax exists. If the brackets
at the end of a refinery command are prefixed by the sequence `[]`, i.e. an opening bracket
followed directly by a closing one, then all outputs of the unit are fused into a single
output chunk by concatenating them. In our example:

    $ emit OOCLOOCL | chop 4 [| snip 2::-1 3 []]]
    COOL
    COOL


### Scoping

It is possible to alter the **visibility** of `refinery.lib.frame.Chunk`, primarily by
using `refinery.scope`. The unit accepts a slice argument which defines the indices of
the current frame that remain visible. All subsequent units will only process visible
chunks and simply forward the ones that are not visible. `refinery.lib.frame.Chunk`s
remain invisible when a new frame layer opens:

    $ emit BINARY REFINERY [| scope 0 | clower | sep - ]
    binary-REFINERY

Here, the scope was limited to the first chunk `BINARY` which was transformed to lower
case, but the second chunk `REFINERY` was left untouched. A somewhat more complex example:

    $ emit aaaaaaaa namtaB [| scope 0 | rex . [| ccp N ]| scope 1 | rev | sep - ]
    NaNaNaNaNaNaNaNa-Batman

Note that `refinery.sep` makes all chunks in the frame visible by default, because it is
intended to sit at the end of a frame. Otherwise, `NaNaNaNaNaNaNaNa` and `Batman` in the
above example would not be separated by a dash.
"""
import copy
import json
import base64
import os

from typing import Iterable, BinaryIO, Callable, Optional, Tuple, Dict, ByteString, Any
from refinery.lib.structures import MemoryFile
from refinery.lib.powershell import is_powershell_process
from refinery.lib.tools import isbuffer

try:
    import msgpack
except ModuleNotFoundError:
    msgpack = None

__all__ = [
    'Chunk',
    'Framed',
    'FrameUnpacker'
]


class BytesEncoder(json.JSONEncoder):
    def default(self, obj):
        if isbuffer(obj):
            return {'_bin': base64.b85encode(obj).decode('ascii')}
        return super().default(obj)


class BytesDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if isinstance(obj, dict) and len(obj) == 1 and '_bin' in obj:
            return base64.b85decode(obj['_bin'])
        return obj


MAGIC = bytes.fromhex(os.environ.get('REFINERY_FRAME_MAGIC', 'C0CAC01AC0DE'))
ISPS1 = is_powershell_process()

if ISPS1:
    MAGIC = B'[[%s]]' % base64.b85encode(MAGIC)


class Chunk(bytearray):
    """
    Represents the individual chunks in a frame. The `refinery.units.Unit.filter` method
    receives an iterable of `refinery.lib.frame.Chunk`s.
    """
    def __init__(
        self,
        data: ByteString,
        path: Tuple[int] = (),
        view: Optional[Tuple[bool]] = None,
        meta: Optional[Dict[str, Any]] = None,
        fill: Optional[bool] = None
    ):
        view = view or (False,) * len(path)
        if len(view) != len(path):
            raise ValueError('skipping must have the same length as path')

        if isinstance(data, Chunk):
            path = path or data.path
            view = view or data.view
            meta = meta or data.meta
            fill = fill or data.fill

        self._view: Tuple[bool] = view
        self._path: Tuple[int] = path
        self._meta: Dict[str, Any] = meta or dict()
        self._fill: bool = fill

        bytearray.__init__(self, data)

    @property
    def fill(self) -> bool:
        return self._fill

    def set_next_scope(self, visible: bool) -> None:
        self._fill = visible

    def truncate(self, gauge):
        self._path = self._path[:gauge]
        self._view = self._view[:gauge]

    def nest(self, *ids):
        """
        Nest this chunk deeper by providing a sequence of indices inside each new layer of the
        frame. The `refinery.lib.frame.Chunk.path` tuple is extended by these values. The
        visibility of the `refinery.lib.frame.Chunk` at each new layer is inherited from its
        current visibility.
        """
        if self._fill is not None:
            self._view += (self.visible,) * (len(ids) - 1) + (self._fill,)
            self._fill = None
        else:
            self._view += (self.visible,) * len(ids)
        self._path += ids
        return self

    @property
    def view(self) -> Tuple[bool]:
        """
        This tuple of boolean values indicates the visibility of this chunk at each layer of
        the frame tree. The `refinery.scope` unit can be used to change visibility of chunks
        within a frame.
        """
        return self._view

    @property
    def path(self) -> Tuple[int]:
        """
        The vertices in each frame tree layer are sequentially numbered by their order of
        appearance in the stream. The `refinery.lib.frame.Chunk.path` contains the numbers of
        the vertices (in each layer) which define the path from the root of the frame tree
        to the leaf vertex representing this `refinery.lib.frame.Chunk`
        """
        return self._path

    @property
    def meta(self) -> Dict[str, Any]:
        """
        Every chunk can contain a dictionary of arbitrary metadata.
        """
        return self._meta

    @property
    def visible(self):
        """
        This property defines whether the chunk is currently visible. It defaults to true if the
        chunk is not part of a frame and is otherwise the same as the last element of the tuple
        `refinery.lib.frame.Chunk.view`. Setting this property will correspondingly alter the last
        entry of `refinery.lib.frame.Chunk.view`.
        Setting this property on an unframed `refinery.lib.frame.Chunk` raises an `AttributeError`.
        """
        return not self._view or self._view[~0]

    @property
    def scopable(self):
        """
        This property defines whether the chunk can be made visible in the current frame.
        """
        return len(self._view) <= 1 or self._view[~1]

    @visible.setter
    def visible(self, value: bool):
        if not self._view:
            raise AttributeError('cannot set visibility of chunk outside frame')
        if value != self.visible:
            self._view = self._view[:~0] + (value,)

    def inherit(self, parent):
        """
        This method can be used to take over properties of a parent `refinery.lib.frame.Chunk`.
        """
        self._path = parent._path
        self._view = parent._view
        for key, value in parent._meta.items():
            if key not in self._meta:
                self._meta[key] = value
        return self

    @classmethod
    def unpack(cls, stream):
        """
        Classmethod to read a serialized chunk from an unpacker stream.
        """
        item = next(stream)
        if ISPS1:
            item = json.loads(item, cls=BytesDecoder)
        path, view, meta, fill, data = item
        return cls(data, path, view=view, meta=meta, fill=fill)

    def pack(self):
        """
        Return the serialized representation of this chunk.
        """
        obj = (self._path, self._view, self._meta, self._fill, self)
        if ISPS1:
            packed = json.dumps(obj, cls=BytesEncoder, separators=(',', ':')) + '\n'
            return packed.encode('utf8')
        return msgpack.packb(obj)

    def __repr__(self) -> str:
        layer = '/'.join('#' if not s else str(p) for p, s in zip(self._path, self._view))
        layer = layer and '/' + layer
        metas = ','.join(self._meta)
        metas = metas and F' meta=({metas})'
        return F'<chunk{layer}{metas} size={len(self)} data={repr(bytes(self))}>'

    def __hash__(self):
        return hash((
            len(self),
            bytes(self[:+64]),
            bytes(self[-64:])
        ))

    def __getitem__(self, bounds):
        if isinstance(bounds, str):
            return self._meta[bounds]
        return bytearray.__getitem__(self, bounds)

    def __setitem__(self, bounds, value):
        if isinstance(bounds, str):
            self._meta[bounds] = value
        else:
            bytearray.__setitem__(self, bounds, value)

    def __copy__(self):
        return Chunk(self, self._path, self._view, self._meta, self._fill)

    def __deepcopy__(self, memo):
        copy = Chunk(self, self._path, self._view, self._fill)
        memo[id(self)] = copy
        copy._meta = copy.deepcopy(self._meta, memo)
        return copy


class FrameUnpacker:
    """
    Provides a unified interface to read both framed and raw input data from a stream. After
    loading a framed input stream, the object provides an iterator over the first **frame** in
    the bottom **layer** of the frame tree. Consider this doubly layered frame tree:

        [[FOO, BAR], [BOO, BAZ]]

    The `refinery.lib.frame.FrameUnpacker` object will first be an iterator over the first frame
    `[FOO, BAR]`. After consuming this iterator, the `refinery.lib.frame.FrameUnpacker.nextframe`
    method can be called to load the next frame, at which point the object will become an
    iterator over `[BOO, BAZ]`.
    """
    def __init__(self, stream: Optional[BinaryIO]):
        self.finished = False
        self.trunk = ()
        self._next = Chunk(bytearray(), ())
        buffer = stream and stream.read(len(MAGIC)) or B''
        if buffer == MAGIC:
            self.framed = True
            self.stream = stream
            if not ISPS1:
                self.unpacker = msgpack.Unpacker(max_buffer_size=0xFFFFFFFF, use_list=False)
            self._advance()
            self.gauge = len(self._next.path)
        else:
            self.framed = False
            self.gauge = 0
            while buffer:
                self._next.extend(buffer)
                buffer = stream.read()

    def _advance(self) -> None:
        while not self.finished:
            try:
                stream = self.stream if ISPS1 else self.unpacker
                self._next = Chunk.unpack(stream)
                break
            except StopIteration:
                pass
            try:
                recv = self.stream.read1() or self.stream.read()
            except TypeError:
                recv = self.stream.read()
            if recv:
                self.unpacker.feed(recv)
                continue
            self.finished = True

    def nextframe(self) -> bool:
        """
        Once the iterator is consumed, calling this function will return `True` if
        and only if another frame with input data has been loaded, in which case
        the object will provide an iterator over the freshly loaded frame. If this
        function returns `False`, all input data has been consumed.
        """
        if self.finished:
            return False
        self.trunk = self._next.path
        return True

    @property
    def eol(self) -> bool:
        return self.trunk != self.peek

    @property
    def peek(self) -> Tuple[int]:
        """
        Contains the identifier of the next frame.
        """
        return self._next.path

    def __iter__(self) -> Iterable[Chunk]:
        if self.finished:
            return
        if not self.framed:
            yield self._next
            self.finished = True
            return
        while not self.finished and self.trunk == self._next.path:
            yield self._next
            self._advance()


class Framed:
    """
    A proxy interface to ingest and output framed data. It is given an `action` to be
    performed for each elementary chunk of data, a `stream` of input data, and an integer
    argument `nested` which specifies the relative amount of nesting to be performed
    by the interface. This parameter should either be `1` if the interface should output
    the results at an additional layer, `0` if the nesting depth of the data should
    remain unchanged, and a negative amount if frame layers are to be collapsed. After
    initialization, the `refinery.lib.frame.Framed` object is an iterator that yields
    bytestrings which can be forwarded as the output of the operation with all framing
    already taken care of.
    """
    def __init__(
        self,
        action : Callable[[bytearray], Iterable[Chunk]],
        stream : BinaryIO,
        nesting: int = 0,
        squeeze: bool = False,
        filter : Optional[Callable[[Iterable[Chunk]], Iterable[Chunk]]] = None,
    ):
        self.unpack = FrameUnpacker(stream)
        self.action = action
        self.filter = filter
        self.nesting = nesting
        self.squeeze = squeeze

    def _apply_filter(self) -> Iterable[Chunk]:

        it = iter(self.unpack)

        def rewind():
            yield top
            yield from it

        try:
            top = next(it)
        except StopIteration:
            pass
        else:
            rw = rewind()
            yield from self.filter(rw) if top.scopable else rw

        if not self.unpack.eol:  # filter did not consume the iterable
            for _ in self.unpack:
                pass

    @property
    def unframed(self) -> bool:
        """
        This property is true if the output data is not framed.
        """
        return self.nesting < 1 and not self.unpack.framed

    @property
    def framebreak(self) -> bool:
        """
        This property will be true if the data generated by this framing interface
        is unframed, and the requested nesting was smaller than required to achieve
        this. In practice, it means that the user has provided more closing brakcets
        than were required to close all open frames.
        """
        return self.nesting + self.unpack.gauge < 0

    def _generate_chunks(self, parent: Chunk):
        if not self.squeeze:
            for item in self.action(parent):
                yield copy.copy(item).inherit(parent)
            return
        it = self.action(parent)
        try:
            header = next(it)
        except StopIteration:
            return
        else:
            header.inherit(parent)
            buffer = MemoryFile(header)
            buffer.seek(len(header))
        for item in it:
            buffer.write(item)
        yield header

    def _generate_bytes(self, data: ByteString):
        if not self.squeeze:
            yield from self.action(data)
            return
        buffer = MemoryFile(bytearray())
        for item in self.action(data):
            buffer.write(item)
        yield buffer.getbuffer()

    def __iter__(self):
        if self.unpack.finished:
            return
        if self.nesting > 0:
            yield MAGIC
            rest = (0,) * (self.nesting - 1)
            while self.unpack.nextframe():
                for k, chunk in enumerate(self._apply_filter()):
                    if not chunk.visible:
                        yield chunk.nest(k, *rest).pack()
                        continue
                    for result in self._generate_chunks(chunk):
                        yield result.nest(k, *rest).pack()
        elif not self.unpack.framed:
            for chunk in self._apply_filter():
                yield from self._generate_bytes(chunk)
        elif self.nesting == 0:
            yield MAGIC
            while self.unpack.nextframe():
                for chunk in self._apply_filter():
                    if not chunk.visible:
                        yield chunk.pack()
                        continue
                    for result in self._generate_chunks(chunk):
                        yield result.pack()
        else:
            gauge = max(self.unpack.gauge + self.nesting, 0)
            trunk = None
            if gauge:
                yield MAGIC
            while self.unpack.nextframe():
                while True:
                    for chunk in self._apply_filter():
                        if not trunk:
                            trunk = Chunk(bytearray(), chunk.path, chunk.view, chunk.meta, chunk.fill)
                        results = self._generate_bytes(chunk) if chunk.visible else (chunk,)
                        if not gauge:
                            yield from results
                            continue
                        for result in results:
                            trunk.extend(result)
                    if self.unpack.peek[:gauge + 1] != self.unpack.trunk[:gauge + 1]:
                        break
                    if not self.unpack.nextframe():
                        break
                if not gauge or not trunk:
                    continue
                trunk.truncate(gauge)
                yield trunk.pack()
                trunk = None
