#!/bin/bash

echo "🔨 Building Java PDF to Excel Converter..."

# Download required JAR files if not present
if [ ! -f "pdfbox-app-2.0.28.jar" ]; then
    echo "📥 Downloading Apache PDFBox..."
    wget -q https://archive.apache.org/dist/pdfbox/2.0.28/pdfbox-app-2.0.28.jar
fi

if [ ! -f "tabula-java.jar" ]; then
    echo "📥 Downloading Tabula..."
    wget -q -O tabula-java.jar https://github.com/tabulapdf/tabula-java/releases/download/v1.0.5/tabula-1.0.5-jar-with-dependencies.jar
fi

if [ ! -f "poi-5.2.3.jar" ]; then
    echo "📥 Downloading Apache POI..."
    wget -q https://repo1.maven.org/maven2/org/apache/poi/poi/5.2.3/poi-5.2.3.jar
    wget -q https://repo1.maven.org/maven2/org/apache/poi/poi-ooxml/5.2.3/poi-ooxml-5.2.3.jar
    wget -q https://repo1.maven.org/maven2/org/apache/poi/poi-ooxml-schemas/4.1.2/poi-ooxml-schemas-4.1.2.jar
    wget -q https://repo1.maven.org/maven2/org/apache/xmlbeans/xmlbeans/5.1.1/xmlbeans-5.1.1.jar
    wget -q https://repo1.maven.org/maven2/org/apache/commons/commons-compress/1.21/commons-compress-1.21.jar
    wget -q https://repo1.maven.org/maven2/commons-codec/commons-codec/1.15/commons-codec-1.15.jar
    wget -q https://repo1.maven.org/maven2/org/apache/commons/commons-collections4/4.4/commons-collections4-4.4.jar
    wget -q https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-api/2.18.0/log4j-api-2.18.0.jar
    wget -q https://repo1.maven.org/maven2/org/apache/logging/log4j/log4j-core/2.18.0/log4j-core-2.18.0.jar
fi

# Create classpath
CLASSPATH=".:pdfbox-app-2.0.28.jar:tabula-java.jar:poi-5.2.3.jar:poi-ooxml-5.2.3.jar:poi-ooxml-schemas-4.1.2.jar:xmlbeans-5.1.1.jar:commons-compress-1.21.jar:commons-codec-1.15.jar:commons-collections4-4.4.jar:log4j-api-2.18.0.jar:log4j-core-2.18.0.jar"

# Compile
echo "📦 Compiling..."
javac -cp "$CLASSPATH" PDFToExcelConverter.java

if [ $? -eq 0 ]; then
    echo "✅ Compilation successful!"
    
    # Run converter
    echo ""
    echo "🚀 Running converter..."
    java -cp "$CLASSPATH" PDFToExcelConverter "$@"
else
    echo "❌ Compilation failed!"
    exit 1
fi