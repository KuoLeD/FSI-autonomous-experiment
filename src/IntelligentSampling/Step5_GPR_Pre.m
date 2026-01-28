function output5 = Step5_GPR_Pre(stepn,filenametxt,filenamecsv,pre_txt)
%% 5 基于高斯过程回归，以试验数据为训练数据，对其他范围下水动力系数进行预测 DPQ
% 选取合适的核函数及参数（需要完成交叉验证），基于最大似然估计求解超参数，建立回归模型
% 基于建立的回归模型预测设定范围内的结果，并得到预测结果的置信区间（对结果可信度进行初判）
output5=stepn;
% 读取设定预测值
data = readtable(filenamecsv);
csv_coe = table2array(data (:,16:20));

input0=importdata(filenametxt);
ytrain_direction=input0.data(26);
ytrain_type=input0.data(27);

input0=importdata(pre_txt);
A10=input0.data(5);
StepA1=input0.data(6);
A1end=input0.data(7);
f10=input0.data(8);
Stepf1=input0.data(9);
f1end=input0.data(10);
A20=input0.data(11);
StepA2=input0.data(12);
A2end=input0.data(13);
f20=input0.data(14);
Stepf2=input0.data(15);
f2end=input0.data(16);
theta0=input0.data(17);
Steptheta=input0.data(18);
thetaend=input0.data(19);
U0=input0.data(20);
StepU=input0.data(21);
Uend=input0.data(22);
xtrain_type=input0.data(23);
Kernel_fun=input0.data(24);
Basis_fun=input0.data(25);
para.nextpoint_method=input0.data(26);
para.sigma=input0.data(27);
para.explorationratio=input0.data(28);
para.maxEvaluations=input0.data(29);
para.Boundzone=input0.data(30);
para.w_mu=input0.data(31);
para.w_sigma=input0.data(32);
para.lambda=input0.data(33);
para.Dis_Penalty=input0.data(34);
para.Bounds_Penalty=input0.data(35);
para.penalty_w1=input0.data(36);
para.penalty_w2=input0.data(37);
para.Multiply=input0.data(38);
para.JiaoTi_YorN=input0.data(39);
para.JiaoTi_YorN2=input0.data(40);
para.opti_fun=input0.data(41);
para.ConstantSigma=input0.data(42);

Kfun=[floor(Kernel_fun/1000);floor(mod(Kernel_fun,1000)/100);...
      floor(mod(Kernel_fun,100)/10);mod(Kernel_fun,10)];
Bfun=[floor(Basis_fun/1000);floor(mod(Basis_fun,1000)/100);...
      floor(mod(Basis_fun,100)/10);mod(Basis_fun,10)];

if StepA1~=0
    A1non_pre=(A10:StepA1:A1end)'; % CF无因次振幅
else
    A1non_pre=(A10)';
end
if Stepf1~=0
    f1non_pre=(f10:Stepf1:f1end)'; % CF无因次频率
else
    f1non_pre=(f10)';
end
if StepA2~=0
    A2non_pre=(A20:StepA2:A2end)'; % IL
else
    A2non_pre=(A20)'; % IL
end
if Stepf2~=0
    f2non_pre=(f20:Stepf2:f2end)';
else
    f2non_pre=(f20)'; % IL
end
if Steptheta~=0
    theta_pre=(theta0:Steptheta:thetaend)';
else
    theta_pre=(theta0)'; % CF和IL相位差
end
if StepU~=0
    U_pre=(U0:StepU:Uend)';
else
    U_pre=(U0)'; % U 这个待定做 U 0.05-0.2 大致对应Re 0.5e4-2e4
end

n_pre=length(A1non_pre);
[A1, f1, A2, theta, U] = ...
    ndgrid(A1non_pre, f1non_pre, A2non_pre, theta_pre, U_pre);
if sum(A2non_pre)==0
    f2=A2;
else
    f2=2*f1;
end
% 建立训练数据
switch ytrain_direction
    case 2 % 正反取均值作为训练数据
        y_train1 = (csv_coe(1:2:end,:)+csv_coe(2:2:end,:))./2;
    case 1 % 以正向数据为准
        y_train1 = csv_coe(1:2:end,:);
    case 0 % 以反向数据为准
        y_train1 = csv_coe(2:2:end,:);
    case 3 % 以正反数据中ce正值、大值为准
        for iyt=1:2:length(csv_coe(:,1))
            if csv_coe(iyt,1) > csv_coe(iyt+1,1)
                y_train1((iyt+1)/2,:) = csv_coe(iyt,:); % 正向数据大，取正向
            else
                y_train1((iyt+1)/2,:) = csv_coe(iyt+1,:); % 负向数据大，取负向
            end
        end
end
switch ytrain_type
    case 1 % CF
        y_train = y_train1(:,[1,2]);
    case 2 % IL
        y_train = y_train1(:,[3,4]);
    case 3 % CF+IL
        y_train = y_train1(:,[1,2,3,4]);
    case 4 % CF+IL
        y_train = y_train1;
end
save('y_train.mat','y_train');
load('x_train.mat');
x_pre_data_total = [A1(:), f1(:), A2(:), f2(:), theta(:), U(:)];
switch xtrain_type
    case 1 % CF A和f
        x_pre_data = x_pre_data_total(:,[1,2]);
    case 2 % IL A和f
        x_pre_data = x_pre_data_total(:,[3,4]);
    case 3 % CF+IL A、f和θ
        x_pre_data = x_pre_data_total(:,1:5);
    case 4 % CF A、f和Re（U）
        x_pre_data = x_pre_data_total(:,[1,2,6]);
    case 5 % IL A、f和Re（U）
        x_pre_data = x_pre_data_total(:,[3,4,6]);
    case 6 % CF+IL A、f、θ和Re（U）
        x_pre_data = x_pre_data_total;   
end
x_train1=x_train;
x_pre_data1=x_pre_data;
if sum(x_pre_data_total(:,1))~=0 && sum(x_pre_data_total(:,3))~=0
    x_train1(:,4)=[];
    x_pre_data1(:,4)=[];
end
[y_pre_data, y_pre_err, y_pre_sco,next_point_cal]= GRP_pre(x_pre_data1,x_train1,y_train,Kfun,Bfun,para); % n_pre*4个方差
if sum(x_pre_data_total(:,1))~=0 && sum(x_pre_data_total(:,3))~=0    
    for j=length(next_point_cal(1,:)):-1:4
        next_point_cal(:,j+1)=next_point_cal(:,j);
    end
    next_point_cal(:,4)=2*next_point_cal(:,2);
end
save('y_pre_data.mat','y_pre_data');
save('y_pre_err.mat','y_pre_err');
save('y_pre_sco.mat','y_pre_sco');
save('x_pre_data.mat','x_pre_data');

next_point_write=x_pre_data_total(1:length(y_train(1,:)),:);
switch xtrain_type
    case 1 % CF A和f
        next_point_write(1:length(y_train(1,:)),1:2) = next_point_cal;
    case 2 % IL A和f
        next_point_write(1:length(y_train(1,:)),3:4) = next_point_cal;
    case 3 % CF+IL A、f和θ
        next_point_write(1:length(y_train(1,:)),1:5) = next_point_cal;
    case 4 % CF A、f和Re（U）
        next_point_write(1:length(y_train(1,:)),[1,2,6]) = next_point_cal;
    case 5 % IL A、f和Re（U）
        next_point_write(1:length(y_train(1,:)),[3,4,6]) = next_point_cal;
    case 6 % CF+IL A、f、θ和Re（U）
        next_point_write(1:length(y_train(1,:)),1:6) = next_point_cal;  
end
save('next_point_write.mat','next_point_write'); % 扩展后的下一个实验点，用于写入文件
save('next_point_cal.mat',"next_point_cal"); % 真正的下一个点，用于分析计算
n_test=length(y_train);
TestNum = ['y_pre_data' num2str(n_test)];
save([TestNum,'.mat'],'y_pre_data');
TestNum1 = ['y_pre_err' num2str(n_test)];
save([TestNum1,'.mat'],'y_pre_err');
return