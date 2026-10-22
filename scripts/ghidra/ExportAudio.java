// Export decompiler output, instructions, call edges, and string references.
// Run only against the copied Windows driver in a disposable Ghidra project.
// @category AudioResearch
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.nio.file.*;
import java.io.*;
import java.nio.charset.StandardCharsets;

public class ExportAudio extends GhidraScript {
    private static String clean(Object value) {
        return String.valueOf(value).replace("\t", "\\t").replace("\r", "\\r").replace("\n", "\\n");
    }

    public void run() throws Exception {
        Path out = Paths.get(getScriptArgs()[0]);
        Files.createDirectories(out.resolve("functions"));
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        int successes = 0, failures = 0;
        try (BufferedWriter index = Files.newBufferedWriter(out.resolve("functions.tsv"));
             BufferedWriter calls = Files.newBufferedWriter(out.resolve("calls.tsv"));
             BufferedWriter strings = Files.newBufferedWriter(out.resolve("strings.tsv"))) {
            index.write("address\tname\tsize\tdecompiled\n");
            calls.write("caller\tcallsite\ttarget\ttarget_name\n");
            strings.write("address\tvalue\txref\tfunction\n");
            FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
            while (functions.hasNext() && !monitor.isCancelled()) {
                Function function = functions.next();
                if (function.isExternal()) continue;
                DecompileResults result = decompiler.decompileFunction(function, 60, monitor);
                String address = function.getEntryPoint().toString();
                boolean ok = result.decompileCompleted() && result.getDecompiledFunction() != null;
                if (ok) successes++; else failures++;
                index.write(address + "\t" + clean(function.getName()) + "\t" +
                            function.getBody().getNumAddresses() + "\t" + ok + "\n");
                String source = "/* " + address + " " + function.getName() + " */\n" +
                    (ok ? result.getDecompiledFunction().getC() : "/* FAILED: " + result.getErrorMessage() + " */\n");
                Files.writeString(out.resolve("functions").resolve(address + ".c"), source, StandardCharsets.UTF_8);
                try (BufferedWriter asm = Files.newBufferedWriter(out.resolve("functions").resolve(address + ".asm"))) {
                    InstructionIterator instructions = currentProgram.getListing().getInstructions(function.getBody(), true);
                    while (instructions.hasNext()) {
                        Instruction instruction = instructions.next();
                        asm.write(instruction.getAddress() + "  " + instruction.toString() + "\n");
                        if (instruction.getFlowType().isCall()) {
                            for (Reference ref : instruction.getReferencesFrom()) {
                                if (!ref.getReferenceType().isFlow() && !ref.getReferenceType().isRead()) continue;
                                Symbol symbol = currentProgram.getSymbolTable().getPrimarySymbol(ref.getToAddress());
                                calls.write(address + "\t" + instruction.getAddress() + "\t" + ref.getToAddress() +
                                            "\t" + (symbol == null ? "" : clean(symbol.getName())) + "\n");
                            }
                        }
                    }
                }
            }
            DataIterator data = currentProgram.getListing().getDefinedData(true);
            while (data.hasNext()) {
                Data item = data.next();
                if (!item.hasStringValue()) continue;
                ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(item.getAddress());
                boolean referenced = false;
                while (refs.hasNext()) {
                    referenced = true;
                    Reference ref = refs.next();
                    Function fn = currentProgram.getFunctionManager().getFunctionContaining(ref.getFromAddress());
                    strings.write(item.getAddress() + "\t" + clean(item.getValue()) + "\t" + ref.getFromAddress() +
                                  "\t" + (fn == null ? "" : fn.getEntryPoint().toString()) + "\n");
                }
                if (!referenced) strings.write(item.getAddress() + "\t" + clean(item.getValue()) + "\t\t\n");
            }
        } finally {
            decompiler.dispose();
        }
        println("EXPORT completed: " + successes + " functions; " + failures + " failures");
    }
}
