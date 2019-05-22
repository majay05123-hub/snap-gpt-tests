package org.esa.snap.test;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.apache.commons.io.FileUtils;
import org.apache.commons.io.filefilter.TrueFileFilter;
import org.apache.commons.io.filefilter.WildcardFileFilter;
import org.esa.snap.core.dataio.ProductIO;
import org.esa.snap.core.datamodel.Product;
import org.esa.snap.dataio.ContentAssert;
import org.esa.snap.dataio.ExpectedDataset;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;


/**
 * Created by obarrile on 20/02/2019.
 */
public class TestExecutor {
    public static boolean executeTest(GraphTest graphTest, Path graphFolder, Path inputFolder, Path expectedOutputFolder, Path tempFolder, Path snapBin) throws IOException {

        boolean testPassed = true;
        //prepare parameters
        ArrayList<String> params = new ArrayList<>();
        if(snapBin != null) {
            params.add(snapBin.resolve("gpt").toString());
        } else {
            params.add("gpt");
        }
        params.add(graphFolder.resolve(graphTest.getGraphPath()).toString());

        //inputs
        for(Map.Entry<String, String> entry : graphTest.getInputs().entrySet()) {
            String value = entry.getValue();
            value.replaceAll("\\$graphFolder",graphFolder.toString());
            value.replaceAll("\\$inputFolder",inputFolder.toString());
            value.replaceAll("\\$expectedOutputFolder",expectedOutputFolder.toString());
            value.replaceAll("\\$tempFolder",tempFolder.toString());
            params.add(String.format("-P%s=%s", entry.getKey(), inputFolder.resolve(value).toString()));
        }

        //parameters
        for(Map.Entry<String, String> entry : graphTest.getParameters().entrySet()) {
            String value = entry.getValue();
            value.replaceAll("\\$graphFolder",graphFolder.toString());
            value.replaceAll("\\$inputFolder",inputFolder.toString());
            value.replaceAll("\\$expectedOutputFolder",expectedOutputFolder.toString());
            value.replaceAll("\\$tempFolder",tempFolder.toString());
            params.add(String.format("-P%s=%s",entry.getKey(),value));
        }

        //outputs
        for(Output output : graphTest.getOutputs()) {
            String value = output.getOutputName();
            value.replaceAll("\\$graphFolder",graphFolder.toString());
            value.replaceAll("\\$inputFolder",inputFolder.toString());
            value.replaceAll("\\$expectedOutputFolder",expectedOutputFolder.toString());
            value.replaceAll("\\$tempFolder",tempFolder.toString());
            params.add(String.format("-P%s=%s",output.getParameter(), tempFolder.resolve(value).toString()));
        }

        //execute graph
        ProcessBuilder builder = new ProcessBuilder(params);
        Map<String, String> environ = builder.environment();

        File redirectOutputFile = new File(tempFolder.resolve(graphTest.getId()).toString() + "_gptOutput.txt");
        builder.redirectErrorStream(true);
        builder.redirectOutput(redirectOutputFile);

        List<String> command = builder.command();
        Process process = builder.start();
        try {
            process.waitFor();
        } catch (InterruptedException e) {
            e.printStackTrace();
            return false;
        }

        //check outputs
        for(Output output : graphTest.getOutputs()) {
            final ObjectMapper mapper = new ObjectMapper();
            boolean expectedIsDefined = true;
            if(output.getExpected() == null || output.getExpected().length() == 0) {
                expectedIsDefined = false;
            }

            String outputNameWithExtension = findOutput(output, tempFolder);
            if(outputNameWithExtension == null) {
                System.out.println("Output not found!!!");
                return false;
            }

            if(expectedIsDefined) { //if expected output is not defined, then skip this step
                Product product = ProductIO.readProduct(outputNameWithExtension);
                final ExpectedDataset expectedDataset = mapper.readValue(new File(expectedOutputFolder.resolve(output.getExpected()).toString()), ExpectedDataset.class);
                if(product == null){
                    System.out.println("Cannot read output file: " + outputNameWithExtension);
                    testPassed = false;
                    break;
                }
                final ContentAssert contentAssert = new ContentAssert(expectedDataset.getExpectedContent(), output.getOutputName(), product);
                try {
                    contentAssert.assertProductContent();

                } catch (AssertionError e) {
                    System.out.println("Error in test!!!");
                    System.out.println(e.getMessage());
                    testPassed = false;
                }
            }

        }

        return testPassed;
    }
    private static String findOutput (Output output, Path tempFolder) {
        Collection<File> filelist = FileUtils.listFiles(tempFolder.toFile(), new WildcardFileFilter(String.format("%s.*",output.getOutputName())), null);
        if(filelist.size() == 1) {
            File[] files = filelist.toArray(new File[filelist.size()]);
            return files[0].getAbsolutePath();
        }
        Path outPath = tempFolder.resolve(output.getOutputName());
        if(Files.exists(outPath)) {
            return outPath.toAbsolutePath().toString();
        }

        //TODO check
        return null;
    }
}
