# Import the pika library for RabbitMQ
import pika
import json
import pyodbc

# Establish a connection to the RabbitMQ server
credentials = pika.PlainCredentials('brian', 'brian')
connection = pika.BlockingConnection(pika.ConnectionParameters('10.230.50.63', 5672, 'spot2', credentials))
channel = connection.channel()

# Declare the exchange and the queue to subscribe to
channel.exchange_declare(exchange='spot.exchange', exchange_type='direct')
channel.queue_declare(queue='completenotice.queue', durable=True)

# Bind the queue to the exchange with the routing key
channel.queue_bind(exchange='spot.exchange', queue='completenotice.queue', routing_key='completenotice.route')


# Define a callback function to handle the messages
def callback(ch, method, properties, body):
    print(f"Payload: {body}")

    # Acknowledge the message
    ch.basic_ack(delivery_tag=method.delivery_tag)

    decoded_body = body.decode('utf-8')

    # Replace single quotes with double quotes in the payload
    corrected_body = decoded_body.replace("'", "\"")

    # Parse the payload as a JSON object
    payload = json.loads(corrected_body)

    # Get the MFL Code from the payload
    mfl_code = payload['MFL Code']
    name = payload['Facility']

    if payload.get('Docket') == 'NDWH':

        conn = pyodbc.connect('Driver={SQL Server};'
                              'Server=10.230.50.83;'
                              'Database=DWAPICentral;'
                              'UID=dwh_readonly;'
                              'PWD=c0nstella;')

        # Create a cursor object
        cursor = conn.cursor()

        # Execute the query with the MFL Code
        query = f"""With NewPatientStatus AS (
    SELECT DISTINCT
    P.[PatientCccNumber] AS PatientID, 
    P.[PatientPID] AS PatientPK,
    F.Name AS FacilityName, 
        F.Code AS SiteCode
        ,PS.[ExitDescription] ExitDescription
        ,PS.[ExitDate] ExitDate
        ,PS.[ExitReason] ExitReason
        ,P.[Emr] Emr
        ,CASE P.[Project] 
            WHEN 'I-TECH' THEN 'Kenya HMIS II' 
            WHEN 'HMIS' THEN 'Kenya HMIS II'
        ELSE P.[Project] 
        END AS [Project] 
    
      ,PS.[Voided] Voided
      ,PS.[Processed] Processed
      ,PS.[Created] Created,
    [ReasonForDeath],
    [SpecificDeathReason],
    Cast([DeathDate] as Date)[DeathDate],
    EffectiveDiscontinuationDate,
    PS.TOVerified TOVerified,
    PS.TOVerifiedDate TOVerifiedDate,
    PS.ReEnrollmentDate ReEnrollmentDate
    ,PS.[Date_Created],PS.[Date_Last_Modified]
    FROM
            [DWAPICentral].[dbo].[PatientExtract] P WITH ( NoLock )
        INNER JOIN [DWAPICentral].[dbo].[PatientStatusExtract] PS WITH ( NoLock ) ON PS.[PatientId] = P.ID AND PS.Voided= 0
        INNER JOIN [DWAPICentral].[dbo].[Facility] F ( NoLock ) ON P.[FacilityId] = F.Id AND F.Voided= 0
        INNER JOIN (
            SELECT
                P.PatientPID,
                F.code,
                exitdate,
                MAX ( Ps.Created ) MaxCreated 
            FROM
                [DWAPICentral].[dbo].[PatientExtract] P WITH ( NoLock )
                INNER JOIN [DWAPICentral].[dbo].[PatientStatusExtract] PS WITH ( NoLock ) ON PS.[PatientId] = P.ID 
                AND PS.Voided= 0
                INNER JOIN [DWAPICentral].[dbo].[Facility] F ( NoLock ) ON P.[FacilityId] = F.Id 
                AND F.Voided= 0 
            GROUP BY
                P.PatientPID,
                F.code,
                exitdate 
            ) tn ON P.PatientPID = tn.PatientPID 
            AND f.code = tn.Code 
            AND PS.ExitDate = tn.ExitDate 
            AND PS.Created = tn.MaxCreated 			
        WHERE
            p.gender!= 'Unknown' and F.Code = {mfl_code}
    ),
    NewCtPatient AS (
        SELECT DISTINCT
                        P.ID,P.[PatientCccNumber] as PatientID,P.[PatientPID] as PatientPK,F.Code as SiteCode,F.[Name] as FacilityName,Gender,DOB,RegistrationDate,RegistrationAtCCC
                                        ,RegistrationAtPMTCT,RegistrationAtTBClinic,PatientSource,Region,District,Village
                                       ,ContactRelation,LastVisit,MaritalStatus,EducationLevel,DateConfirmedHIVPositive,PreviousARTExposure,PreviousARTStartDate,P.Emr,P.Project,Orphan,Inschool,null PatientType,null PopulationType,KeyPopulationType,PatientResidentCounty,
                                       PatientResidentSubCounty,PatientResidentLocation,PatientResidentSubLocation,PatientResidentWard,PatientResidentVillage,TransferInDate,Occupation,NUPI
                                       ,Pkv,P.[Date_Created],P.[Date_Last_Modified]
            FROM
                [DWAPICentral].[dbo].[PatientExtract] P WITH ( NoLock )
                INNER JOIN [DWAPICentral].[dbo].[Facility] F WITH ( NoLock ) ON P.[FacilityId] = F.Id 
                AND F.Voided= 0
                INNER JOIN (
                SELECT
                    P.PatientPID,
                    F.code,
                    MAX ( P.created ) MaxCreated 
                FROM
                    [DWAPICentral].[dbo].[PatientExtract] P WITH ( NoLock )
                    INNER JOIN [DWAPICentral].[dbo].[Facility] F WITH ( NoLock ) ON P.[FacilityId] = F.Id 
                    AND F.Voided= 0 
                GROUP BY
                    P.PatientPID,
                    F.code 
                ) tn ON P.PatientPID = tn.PatientPID 
                AND F.code = tn.code 
                AND P.Created = tn.MaxCreated 
            WHERE
                P.Voided= 0 
                AND P.[Gender] IS NOT NULL 
                AND p.gender!= 'Unknown' 
                AND F.code = {mfl_code}
    ),
    NewCTARTPatient AS (
        SELECT DISTINCT
            PA.ID,
            P.[PatientCccNumber] AS PatientID,P.[PatientPID] AS PatientPK,F.Code AS SiteCode,F.Name AS FacilityName, PA.[AgeEnrollment]
                        ,PA.[AgeARTStart],PA.[AgeLastVisit],PA.[RegistrationDate],PA.[PatientSource],PA.[Gender],PA.[StartARTDate],PA.[PreviousARTStartDate]
                        ,PA.[PreviousARTRegimen],PA.[StartARTAtThisFacility],PA.[StartRegimen],PA.[StartRegimenLine],PA.[LastARTDate],PA.[LastRegimen]
                        ,PA.[LastRegimenLine],PA.[Duration],PA.[ExpectedReturn],PA.[Provider],PA.[LastVisit],PA.[ExitReason],PA.[ExitDate],P.[Emr]
                                ,CASE P.[Project] 
                                    WHEN 'I-TECH' THEN 'Kenya HMIS II' 
                                    WHEN 'HMIS' THEN 'Kenya HMIS II'
                                ELSE P.[Project] 
                                END AS [Project]
                                ,PA.[DOB]
    
                        ,PA.[PreviousARTUse]
                        ,PA.[PreviousARTPurpose]
                        ,PA.[DateLastUsed]
                        ,PA.[Date_Created],PA.[Date_Last_Modified] 
        FROM
            [DWAPICentral].[dbo].[PatientExtract] ( NoLock ) P
            INNER JOIN [DWAPICentral].[dbo].[PatientArtExtract] ( NoLock ) PA ON PA.[PatientId] = P.ID 
            AND PA.Voided= 0
            INNER JOIN [DWAPICentral].[dbo].[Facility] ( NoLock ) F ON P.[FacilityId] = F.Id 
            AND F.Voided= 0
            INNER JOIN (
            SELECT
                a.PatientPID,
                c.code,
                MAX ( b.created ) MaxCreated 
            FROM
                [DWAPICentral].[dbo].[PatientExtract] a WITH ( NoLock )
                INNER JOIN [DWAPICentral].[dbo].[PatientArtExtract] b WITH ( NoLock ) ON b.[PatientId] = a.ID 
                AND b.Voided= 0
                INNER JOIN [DWAPICentral].[dbo].[Facility] c WITH ( NoLock ) ON a.[FacilityId] = c.Id 
                AND c.Voided= 0 
            GROUP BY
                a.PatientPID,
                c.code 
            ) tn ON P.PatientPID = tn.PatientPID 
            AND F.code = tn.code 
            AND PA.Created = tn.MaxCreated 
        WHERE
            p.gender!= 'Unknown' AND F.code = {mfl_code}
    ),
    NewCTPatientPharmacy AS (
    SELECT Distinct 
                        P.[PatientCccNumber] AS PatientID, P.[PatientPID] AS PatientPK,F.[Name] AS FacilityName, 
                        F.Code AS SiteCode,PP.[VisitID] VisitID,PP.[Drug] Drug
                      ,PP.[DispenseDate] DispenseDate,PP.[Duration] Duration,
                        PP.[ExpectedReturn] ExpectedReturn,PP.[TreatmentType] TreatmentType
                      ,PP.[PeriodTaken] PeriodTaken,PP.[ProphylaxisType] ProphylaxisType,P.[Emr] Emr
                      ,CASE P.[Project] 
                                WHEN 'I-TECH' THEN 'Kenya HMIS II' 
                                WHEN 'HMIS' THEN 'Kenya HMIS II'
                            ELSE P.[Project] 
                       END AS [Project] 
                      ,PP.[Voided] Voided
                      ,PP.[Processed] Processed
                      ,PP.[Provider] [Provider]
                      ,PP.[RegimenLine] RegimenLine
                      ,PP.[Created] Created
                      ,PP.RegimenChangedSwitched RegimenChangedSwitched
                      ,PP.RegimenChangeSwitchReason RegimenChangeSwitchReason
                      ,PP.StopRegimenReason StopRegimenReason
                      ,PP.StopRegimenDate StopRegimenDate,					  
                      PP.ID, PP.[Date_Created],PP.[Date_Last_Modified]
    
        FROM [DWAPICentral].[dbo].[PatientExtract] P 
        INNER JOIN [DWAPICentral].[dbo].[PatientPharmacyExtract] PP ON PP.[PatientId]= P.ID AND PP.Voided=0
        INNER JOIN [DWAPICentral].[dbo].[Facility] F ON P.[FacilityId] = F.Id AND F.Voided=0
        WHERE p.gender!='Unknown' AND F.Code = {mfl_code}
    ),
    NewPatientVisits AS (
        SELECT DISTINCT
                P.[PatientCccNumber] AS PatientID,
                P.[PatientPID] AS PatientPK,
                F.[Name] AS FacilityName,
                F.Code AS SiteCode,
                PV.[VisitId] VisitID,
                PV.[VisitDate] VisitDate,
                PV.[Service] [SERVICE],
                PV.[VisitType] VisitType,
                PV.[WHOStage] WHOStage,
                PV.[WABStage] WABStage,
                PV.[Pregnant] Pregnant,
                PV.[LMP] LMP,
                PV.[EDD] EDD,
                PV.[Height] [Height],
                PV.[Weight] [Weight],
                PV.[BP] [BP],
                PV.[OI] [OI],
                PV.[OIDate] [OIDate],
                PV.[SubstitutionFirstlineRegimenDate] SubstitutionFirstlineRegimenDate,
                PV.[SubstitutionFirstlineRegimenReason] SubstitutionFirstlineRegimenReason,
                PV.[SubstitutionSecondlineRegimenDate] SubstitutionSecondlineRegimenDate,
                PV.[SubstitutionSecondlineRegimenReason] SubstitutionSecondlineRegimenReason,
                PV.[SecondlineRegimenChangeDate] SecondlineRegimenChangeDate,
                PV.[SecondlineRegimenChangeReason] SecondlineRegimenChangeReason,
                PV.[Adherence] Adherence,
                PV.[AdherenceCategory] AdherenceCategory,
                PV.[FamilyPlanningMethod] FamilyPlanningMethod,
                PV.[PwP] PwP,
                PV.[GestationAge] GestationAge,
                PV.[NextAppointmentDate] NextAppointmentDate,
                P.[Emr] Emr,
        CASE
                    P.[Project] 
                    WHEN 'I-TECH' THEN
                    'Kenya HMIS II' 
                    WHEN 'HMIS' THEN
                    'Kenya HMIS II' ELSE P.[Project] 
                END AS [Project],
                PV.[Voided] Voided,
                pv.[StabilityAssessment] StabilityAssessment,
                pv.[DifferentiatedCare] DifferentiatedCare,
                pv.[PopulationType] PopulationType,
                pv.[KeyPopulationType] KeyPopulationType,
                PV.[Processed] Processed,
                PV.[Created] Created,
                [GeneralExamination],
                [SystemExamination],
                [Skin],
                [Eyes],
                [ENT],
                [Chest],
                [CVS],
                [Abdomen],
                [CNS],
                [Genitourinary],
                PV.VisitBy VisitBy,
                PV.Temp Temp,
                PV.PulseRate PulseRate,
                PV.RespiratoryRate RespiratoryRate,
                PV.OxygenSaturation OxygenSaturation,
                PV.Muac Muac,
                PV.NutritionalStatus NutritionalStatus,
                PV.EverHadMenses EverHadMenses,
                PV.Menopausal Menopausal,
                PV.Breastfeeding Breastfeeding,
                PV.NoFPReason NoFPReason,
                PV.ProphylaxisUsed ProphylaxisUsed,
                PV.CTXAdherence CTXAdherence,
                PV.CurrentRegimen CurrentRegimen,
                PV.HCWConcern HCWConcern,
                PV.TCAReason TCAReason,
                PV.ClinicalNotes ClinicalNotes,
                P.ID AS PatientUnique_ID,
                PV.PatientId AS UniquePatientVisitId,
                PV.ID AS PatientVisitUnique_ID,
                [ZScore],
                [ZScoreAbsolute],
                RefillDate,
                PaedsDisclosure,
                PV.[Date_Created],
                PV.[Date_Last_Modified] 
            FROM
                [DWAPICentral].[dbo].[PatientExtract] P WITH ( NoLock )
                LEFT JOIN [DWAPICentral].[dbo].[PatientArtExtract] PA WITH ( NoLock ) ON PA.[PatientId] = P.ID
                INNER JOIN [DWAPICentral].[dbo].[PatientVisitExtract] PV WITH ( NoLock ) ON PV.[PatientId] = P.ID 
                AND PV.Voided= 0
                INNER JOIN [DWAPICentral].[dbo].[Facility] F WITH ( NoLock ) ON P.[FacilityId] = F.Id 
                AND F.Voided= 0 
            WHERE
                p.gender!= 'Unknown' AND F.Code ={mfl_code}
    ),
     Pharmacy AS (
            SELECT
                ROW_NUMBER()OVER (PARTITION by SiteCode,PatientPK  ORDER BY DispenseDate Desc ) As NUM ,
             SiteCode,
             PatientPK ,
             DispenseDate As LastEncounterDate,
            Case When DATEDIFF(dd,GETDATE(),ExpectedReturn) >= 365 or ExpectedReturn ='1900-01-01' or  ExpectedReturn is null  THEN DATEADD(dd,30,DispenseDate) ELSE ExpectedReturn End as NextAppointmentDate
        FROM NewCTPatientPharmacy  As LastEncounter
        where DispenseDate <= EOMONTH(DATEADD(mm,-1,GETDATE()))
    ),
    
    ART_expected_dates_logic AS (
        SELECT
                    PatientID,
                    SiteCode,
                    PatientPK ,
                    LastVisit,
                    ExpectedReturn,
                    CASE 
                            WHEN DATEDIFF(dd,GETDATE(),ExpectedReturn) <= 365 THEN ExpectedReturn Else DATEADD(day, 30, LastVisit)
                    END AS expected_return_on_365,
                    case when LastVisit is null Then DATEADD(day, 30, LastVisit) else LastVisit End AS last_visit_plus_30_days
        FROM NewCTARTPatient
        where LastVisit <= EOMONTH(DATEADD(mm,-1,GETDATE()))
    ),	
    LatestVisit As (
            Select ROW_NUMBER()OVER (PARTITION by SiteCode,PatientPK  ORDER BY VisitDate Desc ) As NUM,
                    SiteCode,
                    PatientPK ,
                    VisitDate as LastVisitDate,
                    Case When NextAppointmentDate is NULL THEN DATEADD(dd,30,VisitDate) ELSE NextAppointmentDate End as NextAppointmentDate
                    from NewPatientVisits
                    where VisitDate <= EOMONTH(DATEADD(mm,-1,GETDATE()))
    ),
    Patients As (
            Select
            PatientId,
            PatientPK,
            sitecode
            from NewCTARTPatient
    ),
    
    PharmacyART_Visits As (
                    SELECT
                    Patients.PatientID,
                    Patients.PatientPK,
                    Patients.SiteCode,
            Case when Pharmacy.LastencounterDate >=ART_expected_dates_logic.Lastvisit or ART_expected_dates_logic.Lastvisit is null
            Then Pharmacy.LastEncounterDate Else ART_expected_dates_logic.Lastvisit End As LastVisitART_Pharmacy,
             Case when Pharmacy.NextAppointmentdate>=ART_expected_dates_logic.expectedReturn or ART_expected_dates_logic.expectedReturn is null  Then Pharmacy.NextAppointmentdate else ART_expected_dates_logic.expectedReturn End as NextappointmentDate
            from Patients
            left join Pharmacy on  Patients.PatientPk=Pharmacy.PatientPk and Patients.Sitecode=Pharmacy.Sitecode and Num=1
            left join ART_expected_dates_logic on Patients.PatientPk=ART_expected_dates_logic.PatientPk and Patients.Sitecode=ART_expected_dates_logic.Sitecode
    ),
    
    PharmacyART_Computed As (
                    SELECT
                    PharmacyART_Visits.PatientID,
                    PharmacyART_Visits.PatientPK,
                    PharmacyART_Visits.SiteCode,
            Case When PharmacyART_Visits.LastVisitART_Pharmacy >=coalesce(ART_expected_dates_logic.last_visit_plus_30_days, PharmacyART_Visits.LastVisitART_Pharmacy) Then
            PharmacyART_Visits.LastVisitART_Pharmacy Else ART_expected_dates_logic.last_visit_plus_30_days  End As LastEncounterDate,
            NextappointmentDate
            from PharmacyART_Visits
            left join ART_expected_dates_logic on  PharmacyART_Visits.PatientPk=ART_expected_dates_logic.PatientPk and PharmacyART_Visits.Sitecode=ART_expected_dates_logic.Sitecode
    ),
    CombinedVisits As (
            Select
                    PharmacyART_Computed.PatientID,
                    PharmacyART_Computed.PatientPK,
                    PharmacyART_Computed.Sitecode ,
         Case When PharmacyART_Computed.LastEncounterDate >= coalesce(LatestVisit.LastVisitDate, PharmacyART_Computed.LastEncounterDate) THEN PharmacyART_Computed.LastEncounterDate ELSE LatestVisit.LastVisitDate  END AS LastEncounterDate,
         Case  When PharmacyART_Computed.NextappointmentDate>= coalesce (LatestVisit.NextappointmentDate, PharmacyART_Computed.NextappointmentDate) THEN  PharmacyART_Computed.NextappointmentDate else LatestVisit.NextAppointmentDate end as NextAppointmentDate
        from PharmacyART_Computed
            left join LatestVisit on PharmacyART_Computed.PatientPk=LatestVisit.PatientPk and PharmacyART_Computed.Sitecode=LatestVisit.Sitecode and Num=1
    ),
    VistsWithLastEncounter as (
            select 
                    *
            from CombinedVisits
            where LastEncounterDate is not null
    ),
    NewIntermediateLastPatientEncounter AS (
        Select distinct 
                PatientID,
                SiteCode,
                PatientPK ,
                cast( '' as nvarchar(100))PatientPKHash,
                cast( '' as nvarchar(100))PatientIDHash,
                LastEncounterDate,
                CASE 
                        WHEN DATEDIFF(dd,GETDATE(),NextAppointmentDate) <= 365 THEN NextAppointmentDate Else DATEADD(day, 30, LastEncounterDate)
                END AS NextAppointmentDate,
                        cast (getdate() as DATE) as LoadDate
        from CombinedVisits
        where LastEncounterDate <= EOMONTH(DATEADD(mm,-1,GETDATE()))
    
    ),
    NewCTFacilityManifest AS ( 
        SELECT DISTINCT 
            Emr,Project,Voided,Processed,SiteCode,PatientCount,DateRecieved,
            [Name],EmrName,EmrSetup,UploadMode,[Start],[End],Tag
     FROM [DWAPICentral].[dbo].[FacilityManifest](NoLock)
     Where SiteCode = {mfl_code}
    ),
    
    Exits As (
        Select
            ROW_NUMBER() over (PARTITION by PatientPk, Sitecode ORDER by ExitDate DESC) as RowNum,
            PatientPK,
            SiteCode,
            ExitDate,
            ExitReason,
            ExitDescription,
            EffectiveDiscontinuationDate,
            ReasonForDeath,
            ReEnrollmentDate
            from NewPatientStatus
        ),
        Latestexits As (
            select 
            PatientPK,
            SiteCode,
            ExitDate,
            ExitReason,
            ExitDescription,
            EffectiveDiscontinuationDate,
            ReEnrollmentDate,
            ReasonForDeath
            from Exits As Exits
            where RowNum=1 and ExitDate  <=EOMONTH(DATEADD(mm,-1,GETDATE()))
        ),
        
        ARTOutcomes AS (
        Select
            DISTINCT 
                Patients.PatientID, 
                Patients.PatientPK,
                
                ART.startARTDate,
                YEAR(ART.startARTDate) AS Cohort,
                LatestExits.ExitReason,
                LatestExits.ExitDate,
                LastPatientEncounter.LastEncounterDate,
                LastPatientEncounter.NextAppointmentDate,
                CASE
                                When  Latestexits.ExitReason  in ('DIED','dead','Death','Died') THEN 'D'--1
                                WHEN DATEDIFF( dd, ISNULL(LastPatientEncounter.NextAppointmentDate,ART.ExpectedReturn), EOMONTH(DATEADD(mm,-1,GETDATE()))) >30 and LatestExits.ExitReason is null THEN 'uL'--Date diff btw TCA  and Last day of Previous month--2
                                WHEN  LatestExits.ExitDate IS NOT NULL and LatestExits.ExitReason not in ('DIED','dead','Death','Died') and  Latestexits.ReEnrollmentDate between  DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE())-1, 0) and DATEADD(MONTH, DATEDIFF(MONTH, -1, GETDATE())-1, -1) THEN 'V'--3
                                WHEN  LatestExits.ExitDate IS NOT NULL and LatestExits.ExitReason not in ('DIED','dead','Death','Died') and  Latestexits.EffectiveDiscontinuationDate >=  EOMONTH(DATEADD(mm,-1,GETDATE())) THEN 'V'--4
                            WHEN  ART.startARTDate> DATEADD(s,-1,DATEADD(mm, DATEDIFF(m,0,GETDATE()),0)) THEN 'NP'--5
                                WHEN  LatestExits.EffectiveDiscontinuationDate is not null and Latestexits.ReEnrollmentDate is Null Then SUBSTRING(LatestExits.ExitReason,1,1) --6
                                WHEN  LatestExits.ExitDate IS NOT NULL and LatestExits.ExitReason not in ('DIED','dead','Death','Died') and LatestExits.EffectiveDiscontinuationDate between DATEADD(MONTH, DATEDIFF(MONTH, 0, GETDATE())-1, 0) and DATEADD(MONTH, DATEDIFF(MONTH, -1, GETDATE())-1, -1) THEN SUBSTRING(LatestExits.ExitReason,1,1)--When a TO and LFTU has an discontinuationdate during the reporting Month --7
                                WHEN  LatestExits.ExitDate IS NOT NULL and LatestExits.ExitReason not in ('DIED','dead','Death','Died') and  LastPatientEncounter.NextAppointmentDate > EOMONTH(DATEADD(mm,-1,GETDATE()))  THEN 'V'--8
                                WHEN  DATEDIFF( dd, ISNULL(LastPatientEncounter.NextAppointmentDate,ART.ExpectedReturn), EOMONTH(DATEADD(mm,-1,GETDATE()))) <=30 THEN 'V'-- Date diff btw TCA  and LAst day of Previous month-- must not be late by 30 days -- 9
                    WHEN  ISNULL(LastPatientEncounter.NextAppointmentDate,ART.ExpectedReturn) > EOMONTH(DATEADD(mm,-1,GETDATE()))   Then 'V' --10
                                WHEN LastPatientEncounter.NextAppointmentDate IS NULL THEN 'NV' --11
                ELSE SUBSTRING(LatestExits.ExitReason,1,1)
                END
            AS ARTOutcome, 
                     cast (Patients.SiteCode as nvarchar) As SiteCode,
                 Patients.Emr,
                 Patients.Project
                
            FROM NewCtPatient Patients
            INNER JOIN NewCTARTPatient ART  ON  Patients.PatientPK=ART.PatientPK and Patients.Sitecode=ART.Sitecode
            INNER JOIN NewIntermediateLastPatientEncounter  LastPatientEncounter ON   Patients.PatientPK  =LastPatientEncounter.PatientPK   AND Patients.SiteCode  =LastPatientEncounter.SiteCode
            LEFT JOIN  LatestExits   ON  Patients.PatientPK=Latestexits.PatientPK  and Patients.Sitecode=Latestexits.Sitecode
    
                WHERE  ART.startARTDate IS NOT NULL 
    ),
    LatestUpload AS (
    select 
        cast (SiteCode as nvarchar)As SiteCode ,
        Max(DateRecieved) As DateUploaded
     from NewCTFacilityManifest
      group by SiteCode
    ),
    
    LatestVisits AS (
        Select 
        distinct sitecode,
         Max(Visitdate) As SiteAbstractionDate
         from NewPatientVisits
         group by SiteCode
    )
    Select 
            COUNT(*)
     from ARTOutcomes
     left join LatestUpload ON LatestUpload.SiteCode = ARTOutcomes.SiteCode 
     left  join  LatestVisits  ON  LatestVisits.SiteCode = ARTOutcomes.SiteCode
     Where ARTOutcomes.ARTOutcome ='V';"""

        cursor.execute(query)

        # Fetch the results and print them
        results = cursor.fetchall()
        print(f"Results for MFL Code {mfl_code}:")
        for row in results:
            print(row)

        # Connect to the SQL Server database where you want to save the results
        db_connection = pyodbc.connect('Driver={SQL Server};'
                                       'Server=PAL-5CG2114M0C;'
                                       'Database=DwapiCentral;'
                                       'UID=sa;'
                                       'PWD=Megg96Megg;')

        # Create a cursor object for the database connection
        db_cursor = db_connection.cursor()

        merge_query = """
        MERGE INTO DwapiCentral_DQA AS target
        USING (VALUES (?, ?,?,?)) AS source (MFL_Code,Name, Indicator, Value)
        ON target.MFL_Code = source.MFL_Code
        WHEN MATCHED THEN
            UPDATE SET target.Value = source.Value
        WHEN NOT MATCHED THEN
            INSERT (MFL_Code, Name,Indicator,Value) VALUES (source.MFL_Code,source.Name,source.Indicator,source.Value);
        """

        # Iterate through the results and insert them into the database
        for row in results:
            tx_curr = row[0]
            db_cursor.execute(merge_query, mfl_code, name, "TX_CURR", tx_curr)

        # Commit the changes to the database
        db_connection.commit()

        # Close the database connection
        db_connection.close()

        # Close the connection
        conn.close()


# Start consuming the messages from the queue
channel.basic_consume(queue='completenotice.queue', on_message_callback=callback)

# Wait for messages until interrupted
print('Waiting for messages. To exit press CTRL+C')
channel.start_consuming()
