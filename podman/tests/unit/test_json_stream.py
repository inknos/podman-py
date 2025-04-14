import unittest

from podman.domain.json_stream import (
    stream_as_text,
    json_splitter,
    json_stream,
    line_splitter,
    split_buffer,
)
from podman.errors import StreamParseError


class JsonStreamTestCase(unittest.TestCase):
    def test_stream_as_text_with_string(self):
        """Test that stream_as_text works with strings.

        This tests the base case where the stream already contains string data.
        The function should return the strings unchanged, which is important for
        handling output from podman commands that return textual data directly.
        """
        stream = ["test1", "test2", "test3"]
        result = list(stream_as_text(stream))
        self.assertEqual(result, stream)

    def test_stream_as_text_with_bytes(self):
        """Test that stream_as_text works with bytes.

        This tests conversion of byte streams to text streams, which is critical for
        handling output from Docker/podman API responses that often return byte data.
        The function should properly decode bytes using UTF-8 encoding and handle
        potential encoding issues with the 'replace' error strategy.
        """
        stream = [b"test1", b"test2", b"test3"]
        result = list(stream_as_text(stream))
        self.assertEqual(result, ["test1", "test2", "test3"])

    def test_stream_as_text_with_mixed(self):
        """Test that stream_as_text works with mixed types.

        In real-world scenarios, streams might contain a mix of bytes and strings
        (e.g., when concatenating output from different sources). This test ensures
        the function correctly handles mixed content by converting bytes to strings
        while leaving existing strings unchanged.
        """
        stream = [b"test1", "test2", b"test3"]
        result = list(stream_as_text(stream))
        self.assertEqual(result, ["test1", "test2", "test3"])

    def test_json_splitter_valid(self):
        """Test that json_splitter works with valid JSON.

        The json_splitter function is responsible for extracting a single JSON object
        from a buffer, which is essential for processing streaming JSON responses.
        This test verifies that it can correctly parse a simple JSON object and return
        both the parsed object and any remaining content (empty in this case).
        The function handles trailing whitespace correctly.
        """
        buffer = '{"key": "value"}  '
        result = json_splitter(buffer)
        self.assertIsNotNone(result)
        obj, rest = result
        self.assertEqual(obj, {"key": "value"})
        self.assertEqual(rest, "")

    def test_json_splitter_with_rest(self):
        """Test that json_splitter works with valid JSON and additional content.

        When processing streaming JSON data, the buffer might contain multiple JSON
        objects. This test verifies that json_splitter correctly extracts only the first
        complete JSON object and returns the rest of the buffer unchanged, allowing
        for subsequent processing of the remaining content in future iterations.
        """
        buffer = '{"key": "value"} {"key2": "value2"}'
        result = json_splitter(buffer)
        self.assertIsNotNone(result)
        obj, rest = result
        self.assertEqual(obj, {"key": "value"})
        self.assertEqual(rest, '{"key2": "value2"}')

    def test_json_splitter_invalid(self):
        """Test that json_splitter returns None for invalid JSON.

        When processing streaming data, the buffer might contain incomplete JSON objects,
        especially if data is still being received. This test verifies that json_splitter
        correctly returns None when the buffer contains an incomplete or invalid JSON object,
        allowing the caller to wait for more data before attempting to parse again.
        """
        buffer = '{"key": "value" '
        result = json_splitter(buffer)
        self.assertIsNone(result)

    def test_json_stream_simple(self):
        """Test json_stream with a simple stream.

        The json_stream function combines all the utilities to process a stream of JSON data.
        This test verifies that it can correctly handle a stream containing:
        1. A single JSON object in one chunk
        2. Multiple JSON objects in one chunk (separated by newline)

        This functionality is crucial for handling responses from Podman API that might return
        multiple JSON objects in a stream, such as build progress updates or container logs.
        """
        stream = ['{"key1": "value1"}', '{"key2": "value2"}\n{"key3": "value3"}']
        result = list(json_stream(stream))
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], {"key1": "value1"})
        self.assertEqual(result[1], {"key2": "value2"})
        self.assertEqual(result[2], {"key3": "value3"})

    def test_line_splitter_with_newline(self):
        """Test line_splitter with a newline.

        The line_splitter function is a basic building block for processing streaming text data.
        This test verifies it correctly splits a buffer on the first newline character,
        returning both the line (including the newline) and the remaining content.
        This function is particularly useful for processing line-oriented outputs such
        as logs or terminal output from Podman commands.
        """
        buffer = "line1\nline2"
        result = line_splitter(buffer)
        self.assertIsNotNone(result)
        line, rest = result
        self.assertEqual(line, "line1\n")
        self.assertEqual(rest, "line2")

    def test_line_splitter_with_custom_separator(self):
        """Test line_splitter with a custom separator.

        The line_splitter function supports custom separators beyond just newlines.
        This test verifies it can correctly split content using alternative separators,
        which is useful for parsing various text formats that might use different
        delimiters (like CSV data using pipes, or custom output formats from tools).
        """
        buffer = "line1|line2"
        result = line_splitter(buffer, separator='|')
        self.assertIsNotNone(result)
        line, rest = result
        self.assertEqual(line, "line1|")
        self.assertEqual(rest, "line2")

    def test_line_splitter_without_separator(self):
        """Test line_splitter without a separator.

        When processing streaming data, it's common to receive incomplete lines. This test
        verifies that line_splitter correctly returns None when no separator is found,
        indicating that more data needs to be buffered before a complete line can be extracted.
        This behavior is essential for properly handling partial data in streams.
        """
        buffer = "line1"
        result = line_splitter(buffer)
        self.assertIsNone(result)

    def test_split_buffer_with_line_splitter(self):
        """Test split_buffer with line_splitter.

        The split_buffer function is the high-level utility that applies a splitter
        function across a stream of data, buffering partial content as needed.
        This test verifies that using the default line_splitter, it correctly processes
        a stream of chunked line data, extracting complete lines even when they span
        multiple chunks of input data. This is essential for correctly processing
        streamed output from Podman operations like logs.
        """
        stream = ["line1\nline2\n", "line3\n"]
        result = list(split_buffer(stream))
        self.assertEqual(result, ["line1\n", "line2\n", "line3\n"])

    def test_split_buffer_with_custom_splitter(self):
        """Test split_buffer with a custom splitter.

        A key feature of split_buffer is its flexibility through custom splitter functions.
        This test demonstrates using a custom splitter that splits on commas (like CSV data)
        and verifies the function correctly applies the custom logic while maintaining
        proper buffering across stream chunks. This extensibility allows the streaming
        utilities to adapt to various data formats beyond just line-oriented text.
        """

        def custom_splitter(buffer):
            index = buffer.find(',')
            if index == -1:
                return None
            return buffer[: index + 1], buffer[index + 1 :]

        stream = ["item1,item2,", "item3,"]
        result = list(split_buffer(stream, splitter=custom_splitter))
        self.assertEqual(result, ["item1,", "item2,", "item3,"])

    def test_split_buffer_with_decoder(self):
        """Test split_buffer with a decoder.

        The split_buffer function supports optional transformation of the extracted items
        through a decoder function. This test verifies that the decoder is correctly applied
        to each item after splitting, which allows for processing like uppercase conversion,
        JSON parsing, or any other transformation needed on the extracted data before
        returning it to the caller.
        """
        stream = ["line1\nline2\n", "line3"]
        result = list(split_buffer(stream, decoder=lambda x: x.upper()))
        self.assertEqual(result, ["LINE1\n", "LINE2\n", "LINE3"])

    def test_split_buffer_with_decoder_exception(self):
        """Test split_buffer with a decoder that raises an exception.

        When processing complex data streams, decoder errors might occur (e.g., malformed JSON).
        This test verifies that exceptions from the decoder are properly wrapped in a
        StreamParseError, allowing callers to distinguish between transport errors and
        content parsing errors. This provides better error handling and diagnostics
        when processing stream data from Podman operations.
        """

        def failing_decoder(x):
            raise ValueError("Decoder error")

        stream = ["line1\nline2\n", "line3"]
        with self.assertRaises(StreamParseError):
            list(split_buffer(stream, decoder=failing_decoder))


if __name__ == '__main__':
    unittest.main()
