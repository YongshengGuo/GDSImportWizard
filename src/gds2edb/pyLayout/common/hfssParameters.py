#coding:utf-8
#--- coding=utf-8
#--- @Author: Yongsheng.Guo@ansys.com
#--- @Time: 20260704
'''
用于存放HFSS 3D复杂的Array对象，简化程序的可读性。此模块可以被其它模块引用调用预定义的Array对象。
Array List的处理建议使用arrayStruct模块
'''

#EditSetup or InsertSetup的参数列表，建议使用此处的预定义参数，避免在其它模块中直接写死参数，便于维护和修改。
hfssSetup = [
		"NAME:Setup4",
		"SolveType:="		, "Single",
		"Frequency:="		, "12GHz",
		"MaxDeltaS:="		, 0.02,
		"UseMatrixConv:="	, False,
		"MaximumPasses:="	, 50,
		"MinimumPasses:="	, 1,
		"MinimumConvergedPasses:=", 1,
		"PercentRefinement:="	, 30,
		"IsEnabled:="		, True,
		[
			"NAME:MeshLink",
			"ImportMesh:="		, False
		],
		"BasisOrder:="		, 1,
		"DoLambdaRefine:="	, True,
		"DoMaterialLambda:="	, True,
		"SetLambdaTarget:="	, False,
		"Target:="		, 0.3333,
		"UseMaxTetIncrease:="	, False,
		"PortAccuracy:="	, 0.1,
		"UseABCOnPort:="	, False,
		"SetPortMinMaxTri:="	, False,
		"DrivenSolverType:="	, "Direct Solver",
		"EnhancedLowFreqAccuracy:=", False,
		"EnhancedFEBIPreconditioner:=", False,
		"SaveRadFieldsOnly:="	, False,
		"SaveAnyFields:="	, True,
		"IESolverType:="	, "Auto",
		"LambdaTargetForIESolver:=", 0.15,
		"UseDefaultLambdaTgtForIESolver:=", True,
		"IE Solver Accuracy:="	, "Balanced",
		"InfiniteSphereSetup:="	, "",
		"MaxPass:="		, 10,
		"MinPass:="		, 1,
		"MinConvPass:="		, 1,
		"PerError:="		, 1,
		"PerRefine:="		, 30
	]

		# "SolveType:="		, "MultiFrequency",
		# [
		# 	"NAME:MultipleAdaptiveFreqsSetup",
		# 	[
		# 		"NAME:AdaptAt",
		# 		"Frequency:="		, "2.5GHz",
		# 		"Delta:="		, 0.02
		# 	],
		# 	[
		# 		"NAME:AdaptAt",
		# 		"Frequency:="		, "5GHz",
		# 		"Delta:="		, 0.02
		# 	],
		# 	[
		# 		"NAME:AdaptAt",
		# 		"Frequency:="		, "10GHz",
		# 		"Delta:="		, 0.02
		# 	]
		# ],
		# "MaximumPasses:="	, 6,


		# "SolveType:="		, "Broadband",
		# [
		# 	"NAME:MultipleAdaptiveFreqsSetup",
		# 	"Low:="			, "2GHz",
		# 	"High:="		, "20GHz"
		# ],
		# "MaxDeltaS:="		, 0.02,
		# "MaximumPasses:="	, 6,
		# "MinimumPasses:="	, 1,
		# "MinimumConvergedPasses:=", 1,
		# "PercentRefinement:="	, 30,



#InsertFrequencySweep or EditFrequencySweep的参数列表，建议使用此处的预定义参数，避免在其它模块中直接写死参数，便于维护和修改。
hfssSetupSweep = [
		"NAME:Sweep",
		"IsEnabled:="		, True,
		"RangeType:="		, "LinearCount",
		"RangeStart:="		, "2GHz",
		"RangeEnd:="		, "20GHz",
		"RangeCount:="		, 401,
		"Type:="		, "Interpolating",
		"SaveFields:="		, False,
		"SaveRadFields:="	, False,
		"InterpTolerance:="	, 0.5,
		"InterpMaxSolns:="	, 250,
		"InterpMinSolns:="	, 0,
		"InterpMinSubranges:="	, 1,
		"InterpUseS:="		, True,
		"InterpUsePortImped:="	, True,
		"InterpUsePropConst:="	, True,
		"UseDerivativeConvergence:=", False,
		"InterpDerivTolerance:=", 0.2,
		"UseFullBasis:="	, True,
		"EnforcePassivity:="	, True,
		"PassivityErrorTolerance:=", 0.0001,
		"EnforceCausality:="	, False,
		"SMatrixOnlySolveMode:=", "Auto"
	]

#InsertSetup or EditSetup for AutoSolve的参数列表，建议使用此处的预定义参数，避免在其它模块中直接写死参数，便于维护和修改。
hfssAutoSetup = [
		"NAME:Setup5",
		"SolveType:="		, "Auto",
		"IsEnabled:="		, True,
		[
			"NAME:MeshLink",
			"ImportMesh:="		, False
		],
		"AutoSolverSetting:="	, "Balanced",
		[
			"NAME:Sweeps",
			[
				"NAME:Sweep",
				"RangeType:="		, "LinearCount",
				"RangeStart:="		, "0GHz",
				"RangeEnd:="		, "10GHz",
				"RangeCount:="		, 501
			]
		],
		"SaveRadFieldsOnly:="	, False,
		"SaveAnyFields:="	, False,
		"InfiniteSphereSetup:="	, "",
		"Type:="		, "Interpolating"
	]