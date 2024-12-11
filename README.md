# CDL-PLC translator

## General description

cdl-plc translates control sequences in CDL to the IEC 61131-10 XML exchange format. The IEC 61131-10 XML enables exchanging control sequences expressed in the languages according to IEC 61131-3 for industry controllers standardized in IEC 61131.

## CDL-support

The translator supports control sequences including the following CDL blocks:
- Reals.Add
- Reals.MultiplyByParameter
- Reals.Min
 
## Compatibility

- The translator is compatible with CXF JSON-LD files created with the modelica-json translator release 1.2.0.
- The IEC 61131-10 XML import is tested with the PLC ICE Beremiz 1.4-rc1.

## Useful links

- [Modelica-json GitHub page](https://github.com/lbl-srg/modelica-json)
- [Beremiz GitHub page](https://github.com/beremiz/beremiz)

## References

- International Electrotechnical Commission, 2019. Programmable controllers. Part 10: PLC open XML exchange format.
