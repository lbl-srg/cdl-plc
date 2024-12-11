within ModelicaTestCases.CompositeBlocks;
block Custom01

  parameter Real k = 2 "Constant gain";
  parameter Real k2 = 3 "Constant gain";

  Buildings.Controls.OBC.CDL.Interfaces.RealInput yMax "Maximum value of output signal"
    annotation (Placement(transformation(extent={{-134,18},{-94,58}})));

  Buildings.Controls.OBC.CDL.Interfaces.RealInput e "Control error"
    annotation (Placement(transformation(extent={{-116,-44},{-76,-4}})));

  Buildings.Controls.OBC.CDL.Interfaces.RealOutput y "Control signal"
    annotation (Placement(transformation(extent={{160,0},{180,20}})));

  Buildings.Controls.OBC.CDL.Reals.MultiplyByParameter gain(final k=3) "Constant gain"
    annotation (Placement(transformation(extent={{30,6},{50,26}})));

  Buildings.Controls.OBC.CDL.Reals.Min minValue "Outputs the minimum of its inputs"
    annotation (Placement(transformation(extent={{-4,0},{16,20}})));
  Buildings.Controls.OBC.CDL.Reals.MultiplyByParameter gain1(final k=k)
                                                                       "Constant gain"
    annotation (Placement(transformation(extent={{-52,-26},{-32,-6}})));
  Buildings.Controls.OBC.CDL.Reals.Add add2
    annotation (Placement(transformation(extent={{98,-18},{118,2}})));
  Buildings.Controls.OBC.CDL.Interfaces.RealInput uSet
    annotation (Placement(transformation(extent={{-116,-78},{-76,-38}})));
equation

  connect(e, gain1.u) annotation (Line(points={{-96,-24},{-62,-24},{-62,-16},{
          -54,-16}}, color={0,0,127}));
  connect(gain1.y, minValue.u2) annotation (Line(points={{-30,-16},{-16,-16},{
          -16,4},{-6,4}}, color={0,0,127}));
  connect(yMax, minValue.u1) annotation (Line(points={{-114,38},{-16,38},{-16,
          16},{-6,16}}, color={0,0,127}));
  connect(minValue.y, gain.u)
    annotation (Line(points={{18,10},{28,10},{28,16}}, color={0,0,127}));
  connect(gain.y, add2.u1) annotation (Line(points={{52,16},{86,16},{86,-2},{96,
          -2}}, color={0,0,127}));
  connect(uSet, add2.u2) annotation (Line(points={{-96,-58},{86,-58},{86,-14},{
          96,-14}}, color={0,0,127}));
  connect(add2.y, y)
    annotation (Line(points={{120,-8},{170,-8},{170,10}}, color={0,0,127}));
  annotation (Documentation(info="<html>
<p>
Block that outputs <code>y = min(yMax, k*e)</code>,
where
<code>yMax</code> and <code>e</code> are real-valued input signals and
<code>k</code> is a parameter.
</p>
</html>"),
    Diagram(coordinateSystem(extent={{-160,-120},{200,100}})),
    Icon(coordinateSystem(extent={{-160,-120},{200,100}})));
end Custom01;
