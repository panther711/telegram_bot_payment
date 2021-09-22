# Copyright (c) 2021 Emanuele Bellocchia
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

#
# Imports
#
import os
from xml.etree import ElementTree
from typing import Any, Dict, Optional
from telegram_payment_bot.logger import Logger


#
# Classes
#

# Constants for translation loader class
class TranslationLoaderConst:
    # Default language folder
    DEF_LANG_FOLDER = "lang"
    # Default file name
    DEF_FILE_NAME = "lang_en.xml"
    # XML tag for sentences
    SENTENCE_XML_TAG = "sentence"


# Translation loader class
class TranslationLoader:
    # Constructor
    def __init__(self,
                 logger: Logger) -> None:
        self.logger = logger
        self.sentences = {}

    # Load translation file
    def Load(self,
             file_name: Optional[str] = None) -> None:
        def_file_path = os.path.join(os.path.dirname(__file__),
                                     TranslationLoaderConst.DEF_LANG_FOLDER,
                                     TranslationLoaderConst.DEF_FILE_NAME)

        if file_name is not None:
            try:
                self.logger.GetLogger().info("Loading language file '%s'..." % file_name)
                self.__LoadFile(file_name)
            except FileNotFoundError:
                self.logger.GetLogger().error("Language file '%s' not found, loading default language..." % file_name)
                self.__LoadFile(def_file_path)
        else:
            self.logger.GetLogger().info("Loading default language file...")
            self.__LoadFile(def_file_path)

    # Get sentence
    def GetSentence(self,
                    sentence_id: str,
                    placeholders: Optional[Dict[str, Any]] = None) -> str:
        sentence = self.sentences[sentence_id]

        if placeholders is not None:
            for placeholder, value in placeholders.items():
                sentence = sentence.replace("{%s}" % placeholder, str(value))

        return sentence

    # Load file
    def __LoadFile(self,
                   file_name: str) -> None:
        # Parse xml
        tree = ElementTree.parse(file_name)
        root = tree.getroot()

        # Load all sentences
        for child in root:
            if child.tag == TranslationLoaderConst.SENTENCE_XML_TAG:
                sentence_id = child.attrib["id"]
                self.sentences[sentence_id] = child.text.replace("\\n", "\n")

                self.logger.GetLogger().debug("Loaded sentence '%s': %s" % (sentence_id, self.sentences[sentence_id]))

        self.logger.GetLogger().info("Language file successfully loaded, number of sentences: %d" % len(self.sentences))
