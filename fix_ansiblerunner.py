import re
import sys

with open("src/main/java/io/kestra/plugin/ansible/runner/AnsibleRunner.java", "r") as f:
    content = f.read()

# F10: Remove unused imports
content = re.sub(r'import jakarta\.validation\.constraints\.Max;\n', '', content)
content = re.sub(r'import jakarta\.validation\.constraints\.Min;\n', '', content)

# F1 & N2: Static patterns
content = content.replace(
    'private static final java.util.regex.Pattern PKG_ALLOWLIST = java.util.regex.Pattern.compile("^[a-zA-Z0-9_.-]+$");',
    'private static final java.util.regex.Pattern PKG_ALLOWLIST = java.util.regex.Pattern.compile("^[a-zA-Z0-9_][a-zA-Z0-9_\\\\-\\\\.\\\\=\\\\>\\\\<\\\\~]*$");\n    private static final java.util.regex.Pattern WHITESPACE_PATTERN = java.util.regex.Pattern.compile(".*\\\\s.*");'
)

# N2: use static WHITESPACE_PATTERN
content = content.replace(
    'if (arg.matches(".*\\\\s.*") || arg.startsWith("-")) {',
    'if (WHITESPACE_PATTERN.matcher(arg).matches() || arg.startsWith("-")) {'
)

# F4: failOnErrors default description and default evaluation
content = content.replace(
    '@Schema(title = "Fail task if return code is non-zero (default false for programmatic downstream handling)")',
    '@Schema(title = "Fail task if return code is non-zero (default true)")'
)
content = content.replace(
    'boolean failTask = runContext.render(this.failOnErrors).as(Boolean.class).orElse(false);',
    'boolean failTask = runContext.render(this.failOnErrors).as(Boolean.class).orElse(true);'
)

# F2: Path traversal replacements
content = content.replace(
    'Path localSource = workingDir.resolve(relSource);',
    'Path localSource = secureResolve(workingDir, relSource);'
)
content = content.replace(
    'Path localScript = workingDir.resolve(scriptStr.startsWith("/") ? scriptStr.substring(1) : scriptStr);',
    'Path localScript = secureResolve(workingDir, scriptStr.startsWith("/") ? scriptStr.substring(1) : scriptStr);'
)
content = content.replace(
    'Path localSrc = workingDir.resolve(src.startsWith("/") ? src.substring(1) : src);',
    'Path localSrc = secureResolve(workingDir, src.startsWith("/") ? src.substring(1) : src);'
)
content = content.replace(
    'Path localInv = workingDir.resolve(relInv);',
    'Path localInv = secureResolve(workingDir, relInv);'
)
content = content.replace(
    'Path localSubInv = workingDir.resolve("inventory").resolve(relInv);',
    'Path localSubInv = secureResolve(workingDir.resolve("inventory"), relInv);'
)
content = content.replace(
    'Path localPluralInv = workingDir.resolve("inventories").resolve(relInv);',
    'Path localPluralInv = secureResolve(workingDir.resolve("inventories"), relInv);'
)
content = content.replace(
    'Path candPath = workingDir.resolve(cand);',
    'Path candPath = secureResolve(workingDir, cand);'
)

# F15: Spool file permissions
content = content.replace(
    'Path logSpoolFile = Files.createTempFile("ansible-runner-log-" + ident + "-", ".log");',
    '''Path logSpoolFile = Files.createTempFile("ansible-runner-log-" + ident + "-", ".log");
        try {
            Files.setPosixFilePermissions(logSpoolFile, PosixFilePermissions.fromString("rw-------"));
        } catch (UnsupportedOperationException ignored) {
            logSpoolFile.toFile().setReadable(true, true);
            logSpoolFile.toFile().setWritable(true, true);
        }'''
)

# F6: try/finally for cleanup wrapping execution phase
# find the block starting with logConsumer and moving try
content = re.sub(
    r'(AnsibleRunnerLogConsumer logConsumer = new AnsibleRunnerLogConsumer[^;]+;)',
    r'\1\n\n        try {',
    content,
    flags=re.DOTALL
)

# Replace the existing try-catch around run() to merge with the new outer try
content = re.sub(
    r'ScriptOutput scriptOutput;\n\s+try \{\n\s+scriptOutput = commandsWrapper\.run\(\);\n\s+\} catch \(Exception e\) \{\n\s+Files\.deleteIfExists\(logSpoolFile\);\n\s+throw e;\n\s+\} finally \{\n\s+logConsumer\.close\(\);\n\s+FileUtils\.deleteQuietly\(envDir\.toFile\(\)\);\n\s+\}',
    r'''ScriptOutput scriptOutput = commandsWrapper.run();
            int processExitCode = scriptOutput.getExitCode();
            Map<String, URI> extractedOutputFiles = scriptOutput.getOutputFiles();

            // 5. Parse Status, Return Code, and Job Events Telemetry
            Path identArtifactsDir = artifactsBaseDir.resolve(ident);
            ExecutionTelemetry telemetry = parseTelemetry(identArtifactsDir, processExitCode);

            // Check telemetry size against maxOutputsSize
            long maxSize = runContext.render(this.maxOutputsSize).as(Long.class).orElse(DEFAULT_MAX_OUTPUTS_SIZE);
            if (telemetry.stats != null) {
                String statsJson = JacksonMapper.ofJson().writeValueAsString(telemetry.stats);
                if (statsJson.getBytes(StandardCharsets.UTF_8).length > maxSize) {
                    throw new IllegalStateException("Ansible outputs telemetry exceeds the configured maxOutputsSize of " + maxSize + " bytes.");
                }
            }

            // 6. Generate single consolidated results.json file
            URI resultsUri = null;
            boolean shouldSaveResults = runContext.render(this.saveResults).as(Boolean.class).orElse(true);
            if (shouldSaveResults && Files.exists(identArtifactsDir)) {
                Map<String, Object> consolidatedResults = new LinkedHashMap<>();
                consolidatedResults.put("status", telemetry.status);
                consolidatedResults.put("rc", telemetry.rc);
                consolidatedResults.put("summary", telemetry.summary);
                consolidatedResults.put("stats", telemetry.stats);
                consolidatedResults.put("failedHosts", telemetry.failedHosts);
                consolidatedResults.put("failedTasks", telemetry.failedTasks);

                Path resultsFile = workingDir.resolve("results-" + ident + ".json");
                try (OutputStream os = Files.newOutputStream(resultsFile)) {
                    JacksonMapper.ofJson().writerWithDefaultPrettyPrinter().writeValue(os, consolidatedResults);
                }
                resultsUri = runContext.storage().putFile(resultsFile.toFile());
                Files.deleteIfExists(resultsFile);
            }

            // 7. Zip raw artifacts directory
            Path zipFile = workingDir.resolve("artifacts-" + ident + ".zip");
            URI artifactsUri = null;
            boolean shouldSaveArtifacts = runContext.render(this.saveArtifacts).as(Boolean.class).orElse(true);
            if (shouldSaveArtifacts && Files.exists(identArtifactsDir)) {
                ArchiveUtils.zipDirectory(identArtifactsDir, zipFile);
                artifactsUri = runContext.storage().putFile(zipFile.toFile());
            }

            // 8. Store the complete log file
            URI logFileUri = null;
            if ((shouldOutputLogFile || logConsumer.wasTruncated()) && Files.exists(logSpoolFile)) {
                logFileUri = runContext.storage().putFile(logSpoolFile.toFile());
            }
            Files.deleteIfExists(logSpoolFile);

            // 9. Clean up local artifacts if requested
            boolean shouldClean = runContext.render(this.autoCleanArtifacts).as(Boolean.class).orElse(true);
            if (shouldClean) {
                FileUtils.deleteQuietly(artifactsBaseDir.toFile());
                Files.deleteIfExists(zipFile);
            }

            Map<String, URI> finalOutputFiles = (this.outputFiles != null && extractedOutputFiles != null && !extractedOutputFiles.isEmpty())
                ? extractedOutputFiles
                : null;

            boolean shouldOutputSummary = runContext.render(this.outputSummary).as(Boolean.class).orElse(false);

            // 10. Construct Output
            Output output = Output.builder()
                .resultsUri(resultsUri)
                .artifactsUri(artifactsUri)
                .outputLogFile(logFileUri)
                .outputFiles(finalOutputFiles)
                .status(telemetry.status)
                .rc(telemetry.rc)
                .failures(telemetry.summary.getFailures())
                .changed(shouldOutputSummary ? telemetry.summary.getChanged() : null)
                .failedHosts(telemetry.failedHosts)
                .stats(telemetry.stats)
                .summary(shouldOutputSummary ? telemetry.summary : null)
                .build();

            boolean failTask = runContext.render(this.failOnErrors).as(Boolean.class).orElse(true);
            if (failTask && !"successful".equalsIgnoreCase(telemetry.status)) {
                throw new RuntimeException("Ansible Runner failed with status '" + telemetry.status + "' and exit code " + telemetry.rc +
                    " on hosts: " + telemetry.failedHosts);
            }

            return output;
        } catch (Exception e) {
            Files.deleteIfExists(logSpoolFile);
            throw e;
        } finally {
            logConsumer.close();
            FileUtils.deleteQuietly(envDir.toFile());
        }''',
    content
)

# And remove the duplicate block of code from lines 456-545 that we just absorbed into the try block
content = re.sub(
    r'int processExitCode = scriptOutput\.getExitCode\(\);.*?return output;\n    \}',
    r'}\n',
    content,
    flags=re.DOTALL
)


with open("src/main/java/io/kestra/plugin/ansible/runner/AnsibleRunner.java", "w") as f:
    f.write(content)

