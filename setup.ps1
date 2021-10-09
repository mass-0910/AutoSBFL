$CurrentDir = Split-Path $MyInvocation.MyCommand.Path
Set-Location $CurrentDir
mkdir ext-modules
Invoke-WebRequest -Uri https://repo1.maven.org/maven2/junit/junit/4.12/junit-4.12.jar -Outfile ext-modules/junit-4.12.jar
Invoke-WebRequest -Uri https://search.maven.org/remotecontent?filepath=org/hamcrest/hamcrest/2.2/hamcrest-2.2.jar -Outfile ext-modules/hamcrest-2.2.jar
Invoke-WebRequest -Uri https://github.com/EvoSuite/evosuite/releases/download/v1.1.0/evosuite-1.1.0.jar -Outfile ext-modules/evosuite-1.1.0.jar
Invoke-WebRequest -Uri https://github.com/EvoSuite/evosuite/releases/download/v1.1.0/evosuite-standalone-runtime-1.1.0.jar -Outfile ext-modules/evosuite-standalone-runtime-1.1.0.jar

# Install XStream
mkdir ext-modules/xstream
Invoke-WebRequest -Uri https://repo1.maven.org/maven2/com/thoughtworks/xstream/xstream-distribution/1.4.18/xstream-distribution-1.4.18-bin.zip -Outfile ext-modules/xstream/xstream.zip
Expand-Archive -Force -Path ext-modules/xstream/xstream.zip -DestinationPath ext-modules/xstream/
Remove-Item ext-modules/xstream/xstream.zip

# Install Jacoco
mkdir ext-modules/jacoco
Invoke-WebRequest -Uri https://search.maven.org/remotecontent?filepath=org/jacoco/jacoco/0.8.7/jacoco-0.8.7.zip -Outfile ext-modules/jacoco/jacoco.zip
Expand-Archive -Force -Path ext-modules/jacoco/jacoco.zip -DestinationPath ext-modules/jacoco/
Remove-Item ext-modules/jacoco/jacoco.zip